from __future__ import annotations

import builtins
from pathlib import Path

import pytest

import camera.source as camera_source_module
import perception.gesture as gesture_module
from manuals.types import ManualStageResult
from perception.types import GestureEvent, GestureSource, GestureType
import scripts.manuals.gesture_wait as gesture_wait_module
from scripts.manuals import run_manual_loop as loop_cli
from scripts.manuals.gesture_wait import (
    GestureManualWait,
    build_gesture_wait,
    loop_action_from_gesture_event,
    loop_action_from_gesture_events,
)


@pytest.mark.parametrize(
    ("gesture_type", "expected"),
    [
        (GestureType.THUMBS_UP, "advance"),
        (GestureType.TWO_FINGERS, "repeat"),
        (GestureType.FIST, "quit"),
        (GestureType.PALM, None),
        (GestureType.ONE_FINGER, None),
        (GestureType.THREE_FINGERS, None),
        (GestureType.NONE, None),
    ],
)
def test_loop_action_from_gesture_event_maps_only_manual_commands(
    gesture_type: GestureType,
    expected: str | None,
) -> None:
    assert loop_action_from_gesture_event(_event(gesture_type)) == expected


def test_loop_action_from_gesture_events_uses_first_mapped_event() -> None:
    events = [
        _event(GestureType.PALM, timestamp_ms=100),
        _event(GestureType.TWO_FINGERS, timestamp_ms=200),
        _event(GestureType.THUMBS_UP, timestamp_ms=300),
    ]

    assert loop_action_from_gesture_events(events) == "repeat"


def test_loop_action_from_gesture_events_accepts_custom_mapping() -> None:
    events = [_event(GestureType.PALM)]

    assert (
        loop_action_from_gesture_events(events, {GestureType.PALM: "advance"})
        == "advance"
    )


def test_loop_action_from_gesture_events_treats_none_as_no_action() -> None:
    events = [_event(GestureType.THUMBS_UP), _event(GestureType.PALM)]

    assert (
        loop_action_from_gesture_events(
            events,
            {GestureType.THUMBS_UP: "none", GestureType.PALM: "advance"},
        )
        == "advance"
    )


def test_default_mapping_leaves_none_gesture_unmapped() -> None:
    assert loop_action_from_gesture_event(_event(GestureType.NONE)) is None


def test_gesture_manual_wait_returns_action_from_synthetic_event_batch() -> None:
    source = _FakeSource()
    service = _FakeGestureService(
        [
            [],
            [_event(GestureType.THUMBS_UP)],
        ]
    )
    wait = GestureManualWait(
        source=source,
        gesture_service=service,
        poll_delay_s=0,
        log_interval_s=0,
        sleeper=lambda seconds: None,
    )

    assert wait("gesture") == "advance"
    wait.close()

    assert source.start_count == 1
    assert source.stop_count == 1
    assert service.close_count == 1
    assert service.processed_frames == ["frame-1", "frame-2"]


def test_gesture_manual_wait_cleanup_is_idempotent() -> None:
    source = _FakeSource()
    service = _FakeGestureService([[_event(GestureType.THUMBS_UP)]])
    wait = GestureManualWait(
        source=source,
        gesture_service=service,
        poll_delay_s=0,
        log_interval_s=0,
    )

    assert wait("gesture") == "advance"
    wait.close()
    wait.close()

    assert source.stop_count == 1
    assert service.close_count == 1


def test_empty_low_confidence_or_unstable_event_batches_keep_waiting() -> None:
    source = _FakeSource()
    service = _FakeGestureService(
        [
            [],
            [],
            [_event(GestureType.FIST)],
        ]
    )
    wait = GestureManualWait(
        source=source,
        gesture_service=service,
        poll_delay_s=0,
        log_interval_s=0,
        sleeper=lambda seconds: None,
    )

    assert wait("gesture") == "quit"
    wait.close()
    assert source.frame_count == 3


def test_unmapped_stable_events_do_not_produce_loop_action() -> None:
    source = _FakeSource()
    service = _FakeGestureService(
        [
            [_event(GestureType.PALM)],
            [_event(GestureType.ONE_FINGER)],
            [_event(GestureType.THREE_FINGERS)],
            [_event(GestureType.TWO_FINGERS)],
        ]
    )
    wait = GestureManualWait(
        source=source,
        gesture_service=service,
        poll_delay_s=0,
        log_interval_s=0,
        sleeper=lambda seconds: None,
    )

    assert wait("gesture") == "repeat"
    wait.close()
    assert source.frame_count == 4


def test_gesture_manual_wait_timeout_returns_quit_by_default() -> None:
    clock = _AdvancingClock(step=0.05)
    wait = GestureManualWait(
        source=_FakeSource(),
        gesture_service=_FakeGestureService([[], [], []]),
        timeout_s=0.1,
        poll_delay_s=0,
        log_interval_s=0,
        clock=clock,
        sleeper=lambda seconds: None,
    )

    assert wait("gesture") == "quit"
    wait.close()


def test_gesture_manual_wait_timeout_can_fallback_to_keyboard() -> None:
    clock = _AdvancingClock(step=0.05)
    calls: list[str] = []

    def fallback(wait_mode: str) -> str:
        calls.append(wait_mode)
        return "repeat"

    wait = GestureManualWait(
        source=_FakeSource(),
        gesture_service=_FakeGestureService([[], [], []]),
        timeout_s=0.1,
        fallback_wait_func=fallback,
        poll_delay_s=0,
        log_interval_s=0,
        clock=clock,
        sleeper=lambda seconds: None,
    )

    assert wait("gesture") == "repeat"
    wait.close()
    assert calls == ["enter"]


def test_build_gesture_wait_accepts_create_source_video_colon_form(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_create_source(source_name: str, **kwargs: object) -> _FakeSource:
        captured["source_name"] = source_name
        captured["kwargs"] = kwargs
        return _FakeSource()

    class FakeGestureService:
        def __init__(self, config: object) -> None:
            captured["config"] = config

        def process_frame(self, frame: object) -> list[GestureEvent]:
            return []

        def close(self) -> None:
            pass

    monkeypatch.setattr(camera_source_module, "create_source", fake_create_source)
    monkeypatch.setattr(gesture_module, "GestureService", FakeGestureService)

    wait = build_gesture_wait(source_name="video:/tmp/clip.mp4", model_path="model.task")

    assert isinstance(wait.source, _FakeSource)
    assert captured["source_name"] == "video:/tmp/clip.mp4"
    assert captured["kwargs"] == {}


def test_build_gesture_wait_requires_video_path_for_video_source() -> None:
    with pytest.raises(ValueError, match="gesture-video-path"):
        build_gesture_wait(source_name="video", model_path="model.task")


def test_build_gesture_wait_normalizes_uppercase_and_none_mapping(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_create_source(source_name: str, **kwargs: object) -> _FakeSource:
        return _FakeSource()

    class FakeGestureService:
        def __init__(self, config: object) -> None:
            pass

        def process_frame(self, frame: object) -> list[GestureEvent]:
            return []

        def close(self) -> None:
            pass

    monkeypatch.setattr(camera_source_module, "create_source", fake_create_source)
    monkeypatch.setattr(gesture_module, "GestureService", FakeGestureService)

    wait = build_gesture_wait(
        source_name="fake",
        model_path="model.task",
        action_mapping={"PALM": "advance", "THUMBS_UP": "none", "NONE": "none"},
    )

    assert wait.action_mapping == {GestureType.PALM: "advance"}


def test_gesture_manual_wait_rejects_non_gesture_wait_mode() -> None:
    wait = GestureManualWait(
        source=_FakeSource(),
        gesture_service=_FakeGestureService([[_event(GestureType.THUMBS_UP)]]),
    )

    with pytest.raises(ValueError, match="Unsupported wait mode"):
        wait("enter")


def test_keyboard_wait_behavior_is_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(builtins, "input", lambda prompt: "")
    assert loop_cli.wait_for_confirmation("enter") == "advance"

    monkeypatch.setattr(builtins, "input", lambda prompt: "r")
    assert loop_cli.wait_for_confirmation("enter") == "repeat"

    monkeypatch.setattr(builtins, "input", lambda prompt: "q")
    assert loop_cli.wait_for_confirmation("enter") == "quit"

    def raise_eof(prompt: str) -> str:
        raise EOFError

    monkeypatch.setattr(builtins, "input", raise_eof)
    assert loop_cli.wait_for_confirmation("enter") == "quit"


def test_cli_parser_accepts_gesture_arguments() -> None:
    parser = loop_cli.build_parser()

    args = parser.parse_args(
        [
            "--wait-mode",
            "gesture",
            "--gesture-source",
            "video",
            "--gesture-video-path",
            "clip.mp4",
            "--gesture-model-path",
            "model.task",
            "--gesture-timeout-s",
            "0.25",
            "--gesture-fallback",
            "enter",
        ]
    )

    assert args.wait_mode == "gesture"
    assert args.gesture_source == "video"
    assert args.gesture_video_path == "clip.mp4"
    assert args.gesture_model_path == "model.task"
    assert args.gesture_timeout_s == 0.25
    assert args.gesture_fallback == "enter"


def test_gesture_startup_failure_fails_fast_without_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _manual_page(tmp_path)
    processed_pages: list[str] = []

    def fail_startup(**kwargs: object) -> object:
        raise RuntimeError("camera unavailable")

    monkeypatch.setattr(gesture_wait_module, "build_gesture_wait", fail_startup)
    monkeypatch.setattr(loop_cli, "process_page", _fake_process_page(processed_pages))

    result = loop_cli.main(
        [
            "--input",
            str(tmp_path),
            "--wait-mode",
            "gesture",
            "--gesture-source",
            "fake",
        ]
    )

    assert result == 1
    assert processed_pages == []
    assert "could not start gesture wait" in capsys.readouterr().out


def test_gesture_startup_failure_can_fallback_to_enter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _manual_page(tmp_path)
    processed_pages: list[str] = []

    def fail_startup(**kwargs: object) -> object:
        raise RuntimeError("camera unavailable")

    monkeypatch.setattr(gesture_wait_module, "build_gesture_wait", fail_startup)
    monkeypatch.setattr(loop_cli, "process_page", _fake_process_page(processed_pages))
    monkeypatch.setattr(builtins, "input", lambda prompt: "q")

    result = loop_cli.main(
        [
            "--input",
            str(tmp_path),
            "--wait-mode",
            "gesture",
            "--gesture-source",
            "fake",
            "--gesture-fallback",
            "enter",
        ]
    )

    output = capsys.readouterr().out
    assert result == 0
    assert processed_pages == ["manual2-c1.png"]
    assert "falling back to keyboard input" in output


def test_gesture_wait_cleanup_runs_when_startup_object_start_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _manual_page(tmp_path)
    wait = _StartupFailWait()

    monkeypatch.setattr(gesture_wait_module, "build_gesture_wait", lambda **kwargs: wait)

    result = loop_cli.main(
        [
            "--input",
            str(tmp_path),
            "--wait-mode",
            "gesture",
            "--gesture-source",
            "fake",
        ]
    )

    assert result == 1
    assert wait.start_count == 1
    assert wait.close_count == 1


def test_gesture_wait_cleanup_runs_on_keyboard_interrupt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _manual_page(tmp_path)
    wait = _StaticWait("advance")

    def interrupt_page(page: Path, **kwargs: object) -> ManualStageResult:
        raise KeyboardInterrupt

    monkeypatch.setattr(gesture_wait_module, "build_gesture_wait", lambda **kwargs: wait)
    monkeypatch.setattr(loop_cli, "process_page", interrupt_page)

    with pytest.raises(KeyboardInterrupt):
        loop_cli.main(
            [
                "--input",
                str(tmp_path),
                "--wait-mode",
                "gesture",
                "--gesture-source",
                "fake",
            ]
        )

    assert wait.start_count == 1
    assert wait.close_count == 1


def test_enter_mode_does_not_construct_gesture_wait(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _manual_page(tmp_path)
    processed_pages: list[str] = []

    def fail_if_called(**kwargs: object) -> object:
        raise AssertionError("gesture wait should not be built in enter mode")

    monkeypatch.setattr(gesture_wait_module, "build_gesture_wait", fail_if_called)
    monkeypatch.setattr(loop_cli, "process_page", _fake_process_page(processed_pages))
    monkeypatch.setattr(builtins, "input", lambda prompt: "q")

    result = loop_cli.main(["--input", str(tmp_path), "--wait-mode", "enter"])

    assert result == 0
    assert processed_pages == ["manual2-c1.png"]


def test_timeout_style_quit_does_not_advance_page(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _manual_page(tmp_path, "manual2-c1.png")
    _manual_page(tmp_path, "manual2-c2.png")
    processed_pages: list[str] = []

    monkeypatch.setattr(loop_cli, "process_page", _fake_process_page(processed_pages))

    result = loop_cli.run_loop(
        tmp_path,
        wait_mode="gesture",
        wait_func=lambda wait_mode: "quit",
    )

    assert result == 0
    assert processed_pages == ["manual2-c1.png"]


class _FakeSource:
    def __init__(self) -> None:
        self.start_count = 0
        self.stop_count = 0
        self.frame_count = 0
        self.started = False

    def start(self) -> None:
        self.start_count += 1
        self.started = True

    def stop(self) -> None:
        self.stop_count += 1
        self.started = False

    def get_frame(self) -> str:
        assert self.started
        self.frame_count += 1
        return f"frame-{self.frame_count}"


class _FakeGestureService:
    def __init__(self, event_batches: list[list[GestureEvent]]) -> None:
        self.event_batches = list(event_batches)
        self.processed_frames: list[object] = []
        self.close_count = 0

    def process_frame(self, frame: object) -> list[GestureEvent]:
        self.processed_frames.append(frame)
        if not self.event_batches:
            return []
        return self.event_batches.pop(0)

    def close(self) -> None:
        self.close_count += 1


class _StaticWait:
    def __init__(self, action: str) -> None:
        self.action = action
        self.start_count = 0
        self.close_count = 0

    def start(self) -> None:
        self.start_count += 1

    def close(self) -> None:
        self.close_count += 1

    def __call__(self, wait_mode: str) -> str:
        return self.action


class _StartupFailWait(_StaticWait):
    def __init__(self) -> None:
        super().__init__("quit")

    def start(self) -> None:
        self.start_count += 1
        raise RuntimeError("source failed")


class _AdvancingClock:
    def __init__(self, *, step: float) -> None:
        self.value = 0.0
        self.step = step

    def __call__(self) -> float:
        self.value += self.step
        return self.value


def _manual_page(tmp_path: Path, name: str = "manual2-c1.png") -> Path:
    page = tmp_path / name
    page.write_bytes(b"synthetic placeholder")
    return page


def _fake_process_page(processed_pages: list[str]):
    def fake_process_page(page: Path, **kwargs: object) -> ManualStageResult:
        processed_pages.append(page.name)
        return ManualStageResult(stage_id=page.stem, active_colors=["green"])

    return fake_process_page


def _event(
    gesture_type: GestureType,
    *,
    timestamp_ms: int = 100,
    confidence: float = 0.9,
) -> GestureEvent:
    return GestureEvent(
        type=gesture_type,
        confidence=confidence,
        source=GestureSource.GEOMETRY,
        timestamp_ms=timestamp_ms,
        handedness="Right",
        hand_index=0,
        raw_label=gesture_type.name,
        raw_label_confidence=confidence,
        camera_name="unit-test",
        frame_id=timestamp_ms,
    )
