from __future__ import annotations

import sys
import types
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest

import perception.gesture as gesture_module
from core.frame import Frame
from core.landmarks import Landmark2D, Landmark3D
from perception.gesture import GestureService, _MediaPipeRuntime
from perception.types import FilterConfig, GestureServiceConfig, GestureSource, GestureType


class FakeImage:
    def __init__(self, *, image_format: object, data: np.ndarray) -> None:
        self.image_format = image_format
        self.data = data


class FakeRecognizer:
    def __init__(self, result: object | None = None) -> None:
        self.result = result or _empty_result()
        self.calls: list[int] = []
        self.closed = False

    def recognize_for_video(self, image: FakeImage, timestamp_ms: int) -> object:
        assert image.image_format == "SRGB"
        self.calls.append(timestamp_ms)
        return self.result

    def close(self) -> None:
        self.closed = True


def test_duplicate_timestamp_raises_value_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    recognizer = FakeRecognizer()
    service = _service(monkeypatch, tmp_path, recognizer)

    service.analyze_frame(_frame(100))
    with pytest.raises(ValueError, match="strictly increasing"):
        service.analyze_frame(_frame(100))

    assert recognizer.calls == [100]


def test_decreasing_timestamp_raises_value_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    recognizer = FakeRecognizer()
    service = _service(monkeypatch, tmp_path, recognizer)

    service.analyze_frame(_frame(100))
    with pytest.raises(ValueError, match="strictly increasing"):
        service.analyze_frame(_frame(99))

    assert recognizer.calls == [100]


def test_strictly_increasing_timestamps_are_accepted(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    recognizer = FakeRecognizer()
    service = _service(monkeypatch, tmp_path, recognizer)

    service.analyze_frame(_frame(100))
    service.analyze_frame(_frame(101))
    service.close()

    assert recognizer.calls == [100, 101]
    assert recognizer.closed


def test_process_frame_runs_inference_once_then_filters(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    recognizer = FakeRecognizer(
        _result(
            raw_label="Thumb_Up",
            raw_confidence=0.92,
        )
    )
    service = _service(monkeypatch, tmp_path, recognizer)

    events = service.process_frame(_frame(100))

    assert recognizer.calls == [100]
    assert [event.type for event in events] == [GestureType.THUMBS_UP]


def test_events_from_observations_does_not_run_inference(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    recognizer = FakeRecognizer()
    service = _service(monkeypatch, tmp_path, recognizer)

    observations = service._build_observations(_result(raw_label="Open_Palm"), _frame(100))
    events = service.events_from_observations(_frame(100), observations)

    assert recognizer.calls == []
    assert [event.type for event in events] == [GestureType.PALM]


def test_build_observations_preserves_phase2_metadata(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    recognizer = FakeRecognizer(_result(raw_label="Closed_Fist", raw_confidence=0.77))
    service = _service(monkeypatch, tmp_path, recognizer)

    observations = service.analyze_frame(
        Frame(
            rgb=np.zeros((4, 5, 3), dtype=np.uint8),
            timestamp_ms=100,
            frame_id=9,
            camera_name="unit-test",
        )
    )

    assert len(observations) == 1
    observation = observations[0]
    assert observation.type is GestureType.FIST
    assert observation.source is GestureSource.HYBRID
    assert observation.raw_label == "Closed_Fist"
    assert observation.raw_label_confidence == 0.77
    assert observation.handedness == "Right"
    assert observation.hand_index == 0
    assert observation.timestamp_ms == 100
    assert observation.frame_id == 9
    assert observation.camera_name == "unit-test"
    assert isinstance(observation.landmarks[0], Landmark2D)
    assert isinstance(observation.world_landmarks[0], Landmark3D)
    assert observation.finger_count == 0
    assert observation.finger_state is not None
    assert observation.finger_state_result is not None


def test_missing_model_raises_clear_error(tmp_path: Path) -> None:
    missing = tmp_path / "missing.task"

    with pytest.raises(FileNotFoundError, match="download_gesture_model.py"):
        GestureService(GestureServiceConfig(model_path=str(missing)))


def test_mediapipe_runtime_uses_video_mode_and_config_values(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, Any] = {}
    fake_mp = SimpleNamespace(
        Image=object,
        ImageFormat=SimpleNamespace(SRGB="SRGB"),
    )

    mp_tasks = types.ModuleType("mediapipe.tasks")
    mp_python = types.ModuleType("mediapipe.tasks.python")
    vision = types.ModuleType("mediapipe.tasks.python.vision")

    class BaseOptions:
        def __init__(self, *, model_asset_path: str) -> None:
            captured["model_asset_path"] = model_asset_path

    class GestureRecognizerOptions:
        def __init__(self, **kwargs: object) -> None:
            captured.update(kwargs)

    class GestureRecognizer:
        @staticmethod
        def create_from_options(options: GestureRecognizerOptions) -> FakeRecognizer:
            captured["created_options"] = options
            return FakeRecognizer()

    mp_python.BaseOptions = BaseOptions
    vision.RunningMode = SimpleNamespace(VIDEO="VIDEO", LIVE_STREAM="LIVE_STREAM")
    vision.GestureRecognizerOptions = GestureRecognizerOptions
    vision.GestureRecognizer = GestureRecognizer
    mp_tasks.python = mp_python
    mp_python.vision = vision

    monkeypatch.setitem(sys.modules, "mediapipe", fake_mp)
    monkeypatch.setitem(sys.modules, "mediapipe.tasks", mp_tasks)
    monkeypatch.setitem(sys.modules, "mediapipe.tasks.python", mp_python)
    monkeypatch.setitem(sys.modules, "mediapipe.tasks.python.vision", vision)

    model_path = _model_path(tmp_path)
    config = GestureServiceConfig(
        model_path=str(model_path),
        max_num_hands=1,
        min_hand_detection_confidence=0.61,
        min_hand_presence_confidence=0.62,
        min_tracking_confidence=0.63,
    )
    runtime = gesture_module._create_mediapipe_runtime(config)

    assert isinstance(runtime.recognizer, FakeRecognizer)
    assert captured["model_asset_path"] == str(model_path)
    assert captured["running_mode"] == "VIDEO"
    assert captured["running_mode"] != "LIVE_STREAM"
    assert captured["num_hands"] == 1
    assert captured["min_hand_detection_confidence"] == 0.61
    assert captured["min_hand_presence_confidence"] == 0.62
    assert captured["min_tracking_confidence"] == 0.63


def _service(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    recognizer: FakeRecognizer,
) -> GestureService:
    monkeypatch.setattr(
        gesture_module,
        "_create_mediapipe_runtime",
        lambda config: _MediaPipeRuntime(
            recognizer=recognizer,
            image_cls=FakeImage,
            image_format="SRGB",
        ),
    )
    return GestureService(
        GestureServiceConfig(
            model_path=str(_model_path(tmp_path)),
            filter_config=FilterConfig(stability_frames=1, cooldown_seconds=0.0),
        )
    )


def _model_path(tmp_path: Path) -> Path:
    model_path = tmp_path / "gesture_recognizer.task"
    model_path.write_bytes(b"fake model for unit tests")
    return model_path


def _frame(timestamp_ms: int) -> Frame:
    return Frame(
        rgb=np.zeros((4, 5, 3), dtype=np.uint8),
        timestamp_ms=timestamp_ms,
        frame_id=timestamp_ms,
        camera_name="unit-test",
    )


def _empty_result() -> object:
    return SimpleNamespace(
        hand_landmarks=[],
        hand_world_landmarks=[],
        gestures=[],
        handedness=[],
    )


def _result(
    *,
    raw_label: str = "Thumb_Up",
    raw_confidence: float = 0.9,
) -> object:
    image_landmarks = _image_landmarks_for_label(raw_label)
    world_landmarks = [
        SimpleNamespace(x=float(index) / 100.0, y=float(index) / 100.0, z=0.0)
        for index in range(21)
    ]
    return SimpleNamespace(
        hand_landmarks=[image_landmarks],
        hand_world_landmarks=[world_landmarks],
        gestures=[[SimpleNamespace(category_name=raw_label, score=raw_confidence)]],
        handedness=[[SimpleNamespace(category_name="Right", score=0.88)]],
    )


def _image_landmarks_for_label(raw_label: str | None) -> list[SimpleNamespace]:
    fingers = {
        "thumb": raw_label == "Thumb_Up",
        "index": raw_label == "Open_Palm",
        "middle": raw_label == "Open_Palm",
        "ring": raw_label == "Open_Palm",
        "pinky": raw_label == "Open_Palm",
    }
    return _image_landmarks(**fingers)


def _image_landmarks(
    *,
    thumb: bool = False,
    index: bool = False,
    middle: bool = False,
    ring: bool = False,
    pinky: bool = False,
) -> list[SimpleNamespace]:
    landmarks = [SimpleNamespace(x=0.5, y=0.5, z=0.0) for _ in range(21)]
    thumb_ip_x = 0.4
    landmarks[3] = SimpleNamespace(x=thumb_ip_x, y=0.5, z=0.0)
    landmarks[4] = SimpleNamespace(
        x=thumb_ip_x + 0.1 if thumb else thumb_ip_x - 0.1,
        y=0.5,
        z=0.0,
    )

    _set_vertical_finger(landmarks, pip_index=6, tip_index=8, extended=index)
    _set_vertical_finger(landmarks, pip_index=10, tip_index=12, extended=middle)
    _set_vertical_finger(landmarks, pip_index=14, tip_index=16, extended=ring)
    _set_vertical_finger(landmarks, pip_index=18, tip_index=20, extended=pinky)
    return landmarks


def _set_vertical_finger(
    landmarks: list[SimpleNamespace],
    *,
    pip_index: int,
    tip_index: int,
    extended: bool,
) -> None:
    landmarks[pip_index] = SimpleNamespace(x=0.5, y=0.5, z=0.0)
    landmarks[tip_index] = SimpleNamespace(
        x=0.5,
        y=0.4 if extended else 0.6,
        z=0.0,
    )
