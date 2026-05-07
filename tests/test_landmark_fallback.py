from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

import perception.gesture as gesture_module
from core.frame import Frame
from perception.gesture import GestureService, _MediaPipeRuntime
from perception.types import FilterConfig, GestureServiceConfig, GestureSource, GestureType


class FakeRecognizer:
    def __init__(self, result: object | None = None) -> None:
        self.result = result
        self.calls: list[int] = []

    def recognize_for_video(self, image: object, timestamp_ms: int) -> object:
        del image
        self.calls.append(timestamp_ms)
        return self.result


class FakeImage:
    def __init__(self, *, image_format: object, data: np.ndarray) -> None:
        self.image_format = image_format
        self.data = data


@pytest.mark.parametrize(
    ("extended", "expected_type", "expected_source"),
    [
        ((True, True, True, True), GestureType.PALM, GestureSource.GEOMETRY),
        ((False, False, False, False), GestureType.FIST, GestureSource.GEOMETRY),
        ((True, True, False, False), GestureType.TWO_FINGERS, GestureSource.GEOMETRY),
    ],
)
def test_none_label_is_preserved_while_geometry_maps_supported_shapes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    extended: tuple[bool, bool, bool, bool],
    expected_type: GestureType,
    expected_source: GestureSource,
) -> None:
    service = _service(monkeypatch, tmp_path)
    result = SimpleNamespace(
        hand_landmarks=[_landmarks(extended)],
        hand_world_landmarks=[],
        gestures=[[SimpleNamespace(category_name="None", score=0.99)]],
        handedness=[],
    )

    observation = service._build_observations(result, _frame())[0]

    assert observation.type is expected_type
    assert observation.source is expected_source
    assert observation.confidence == pytest.approx(
        service.config.gesture_config.default_geometry_confidence
    )
    assert observation.raw_label == "None"
    assert observation.raw_label_confidence == pytest.approx(0.99)


@pytest.mark.parametrize(
    ("raw_label", "expected_type"),
    [
        ("Open_Palm", GestureType.PALM),
        ("Closed_Fist", GestureType.FIST),
    ],
)
def test_canned_labels_remain_primary_over_incompatible_geometry(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    raw_label: str,
    expected_type: GestureType,
) -> None:
    service = _service(monkeypatch, tmp_path)
    result = SimpleNamespace(
        hand_landmarks=[_landmarks((True, False, False, False))],
        hand_world_landmarks=[],
        gestures=[[SimpleNamespace(category_name=raw_label, score=0.88)]],
        handedness=[],
    )

    observation = service._build_observations(result, _frame())[0]

    assert observation.type is expected_type
    assert observation.source is GestureSource.CANNED
    assert observation.raw_label == raw_label
    assert observation.raw_label_confidence == 0.88


def test_missing_raw_label_is_preserved_while_geometry_maps_palm(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    service = _service(monkeypatch, tmp_path)
    result = SimpleNamespace(
        hand_landmarks=[_landmarks((True, True, True, True))],
        hand_world_landmarks=[],
        gestures=[],
        handedness=[],
    )

    observation = service._build_observations(result, _frame())[0]

    assert observation.type is GestureType.PALM
    assert observation.source is GestureSource.GEOMETRY
    assert observation.confidence == pytest.approx(
        service.config.gesture_config.default_geometry_confidence
    )
    assert observation.raw_label is None
    assert observation.raw_label_confidence == pytest.approx(0.0)


def test_process_frame_emits_palm_event_from_geometry_without_rewriting_raw_label(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    service = _service(
        monkeypatch,
        tmp_path,
        _result(raw_label="None", extended=(True, True, True, True)),
    )

    events = service.process_frame(_frame())

    assert [event.type for event in events] == [GestureType.PALM]
    assert events[0].source is GestureSource.GEOMETRY
    assert events[0].raw_label == "None"
    assert events[0].raw_label_confidence == pytest.approx(0.99)
    assert events[0].confidence == pytest.approx(
        service.config.gesture_config.default_geometry_confidence
    )


def test_process_frame_emits_fist_event_from_geometry_without_rewriting_raw_label(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    service = _service(
        monkeypatch,
        tmp_path,
        _result(raw_label="None", extended=(False, False, False, False)),
    )

    events = service.process_frame(_frame())

    assert [event.type for event in events] == [GestureType.FIST]
    assert events[0].source is GestureSource.GEOMETRY
    assert events[0].raw_label == "None"
    assert events[0].raw_label_confidence == pytest.approx(0.99)
    assert events[0].confidence == pytest.approx(
        service.config.gesture_config.default_geometry_confidence
    )


def test_fewer_than_21_landmarks_raise_clear_value_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    service = _service(monkeypatch, tmp_path)
    result = SimpleNamespace(
        hand_landmarks=[_neutral_landmarks(count=20)],
        hand_world_landmarks=[],
        gestures=[[SimpleNamespace(category_name="None", score=0.99)]],
        handedness=[],
    )

    with pytest.raises(ValueError, match="Expected at least 21 hand landmarks"):
        service._build_observations(result, _frame())


def _service(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    result: object | None = None,
) -> GestureService:
    monkeypatch.setattr(
        gesture_module,
        "_create_mediapipe_runtime",
        lambda config: _MediaPipeRuntime(
            recognizer=FakeRecognizer(result),
            image_cls=FakeImage,
            image_format="SRGB",
        ),
    )
    model_path = tmp_path / "gesture_recognizer.task"
    model_path.write_bytes(b"fake model for unit tests")
    return GestureService(
        GestureServiceConfig(
            model_path=str(model_path),
            filter_config=FilterConfig(stability_frames=1, cooldown_seconds=0.0),
        )
    )


def _frame() -> Frame:
    return Frame(
        rgb=np.zeros((4, 5, 3), dtype=np.uint8),
        timestamp_ms=100,
    )


def _landmarks(extended: tuple[bool, bool, bool, bool]) -> list[SimpleNamespace]:
    landmarks = _neutral_landmarks(count=21)
    for is_extended, (tip_index, pip_index) in zip(
        extended,
        [(8, 6), (12, 10), (16, 14), (20, 18)],
        strict=True,
    ):
        landmarks[tip_index].y = 0.2 if is_extended else 0.8
        landmarks[pip_index].y = 0.6
    return landmarks


def _neutral_landmarks(*, count: int) -> list[SimpleNamespace]:
    return [SimpleNamespace(x=0.5, y=0.5, z=0.0) for _ in range(count)]


def _result(
    *,
    raw_label: str,
    extended: tuple[bool, bool, bool, bool],
) -> object:
    return SimpleNamespace(
        hand_landmarks=[_landmarks(extended)],
        hand_world_landmarks=[],
        gestures=[[SimpleNamespace(category_name=raw_label, score=0.99)]],
        handedness=[],
    )
