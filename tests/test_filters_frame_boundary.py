import numpy as np
import pytest

from core.frame import Frame
from perception.filters import FilterChain
from perception.types import FilterConfig, GestureObservation, GestureSource, GestureType


_DEFAULT_FRAME_ID = object()


def test_matching_frame_boundary_fields_pass_and_event_preserves_metadata() -> None:
    chain = FilterChain(FilterConfig(stability_frames=1, cooldown_seconds=0.0))
    observation = _observation(timestamp_ms=100, frame_id=7, camera_name="cam-a")
    frame = _frame(timestamp_ms=100, frame_id=7, camera_name="cam-a")

    events = chain.apply([observation], frame=frame)

    assert len(events) == 1
    event = events[0]
    assert event.type is GestureType.THUMBS_UP
    assert event.confidence == observation.confidence
    assert event.source is observation.source
    assert event.timestamp_ms == 100
    assert event.handedness == observation.handedness
    assert event.hand_index == observation.hand_index
    assert event.finger_count == observation.finger_count
    assert event.finger_state == observation.finger_state
    assert event.raw_label == observation.raw_label
    assert event.raw_label_confidence == observation.raw_label_confidence
    assert event.camera_name == "cam-a"
    assert event.frame_id == 7


def test_mismatched_timestamp_raises_value_error() -> None:
    chain = FilterChain(FilterConfig(stability_frames=1, cooldown_seconds=0.0))

    with pytest.raises(ValueError, match="timestamp_ms"):
        chain.apply([_observation(timestamp_ms=99)], frame=_frame(timestamp_ms=100))


def test_mismatched_camera_name_raises_value_error() -> None:
    chain = FilterChain(FilterConfig(stability_frames=1, cooldown_seconds=0.0))

    with pytest.raises(ValueError, match="camera_name"):
        chain.apply(
            [_observation(timestamp_ms=100, camera_name="cam-a")],
            frame=_frame(timestamp_ms=100, camera_name="cam-b"),
        )


def test_mismatched_frame_id_raises_when_both_are_present() -> None:
    chain = FilterChain(FilterConfig(stability_frames=1, cooldown_seconds=0.0))

    with pytest.raises(ValueError, match="frame_id"):
        chain.apply(
            [_observation(timestamp_ms=100, frame_id=1)],
            frame=_frame(timestamp_ms=100, frame_id=2),
        )


def test_none_frame_id_is_treated_as_unknown_and_allowed() -> None:
    chain = FilterChain(FilterConfig(stability_frames=1, cooldown_seconds=0.0))

    events_from_unknown_observation = chain.apply(
        [_observation(timestamp_ms=100, frame_id=None)],
        frame=_frame(timestamp_ms=100, frame_id=1),
    )
    events_from_unknown_frame = chain.apply(
        [_observation(timestamp_ms=200, frame_id=2)],
        frame=_frame(timestamp_ms=200, frame_id=None),
    )

    assert len(events_from_unknown_observation) == 1
    assert len(events_from_unknown_frame) == 1


def test_empty_observations_are_valid_and_reset_stability() -> None:
    chain = FilterChain(FilterConfig(stability_frames=2, cooldown_seconds=0.0))

    assert chain.apply([_observation(timestamp_ms=100)], frame=_frame(100)) == []
    assert chain.apply([], frame=_frame(200)) == []
    assert chain.apply([_observation(timestamp_ms=300)], frame=_frame(300)) == []
    events = chain.apply([_observation(timestamp_ms=400)], frame=_frame(400))

    assert [event.type for event in events] == [GestureType.THUMBS_UP]


def test_one_apply_call_represents_exactly_one_frame() -> None:
    chain = FilterChain(FilterConfig(stability_frames=2, cooldown_seconds=0.0))
    same_frame_observations = [
        _observation(timestamp_ms=100, hand_index=0),
        _observation(timestamp_ms=100, hand_index=1),
    ]

    assert chain.apply(same_frame_observations, frame=_frame(100)) == []
    events = chain.apply([_observation(timestamp_ms=200)], frame=_frame(200))

    assert [event.type for event in events] == [GestureType.THUMBS_UP]


def _frame(
    timestamp_ms: int,
    *,
    frame_id: int | None | object = _DEFAULT_FRAME_ID,
    camera_name: str | None = "unit-test",
) -> Frame:
    frame_id_value = timestamp_ms if frame_id is _DEFAULT_FRAME_ID else frame_id
    return Frame(
        rgb=np.zeros((2, 2, 3), dtype=np.uint8),
        timestamp_ms=timestamp_ms,
        frame_id=frame_id_value,
        camera_name=camera_name,
    )


def _observation(
    *,
    timestamp_ms: int,
    frame_id: int | None | object = _DEFAULT_FRAME_ID,
    camera_name: str | None = "unit-test",
    hand_index: int = 0,
) -> GestureObservation:
    frame_id_value = timestamp_ms if frame_id is _DEFAULT_FRAME_ID else frame_id
    return GestureObservation(
        type=GestureType.THUMBS_UP,
        confidence=0.9,
        source=GestureSource.HYBRID,
        timestamp_ms=timestamp_ms,
        handedness="Right",
        hand_index=hand_index,
        finger_count=1,
        raw_label="Thumb_Up",
        raw_label_confidence=0.9,
        camera_name=camera_name,
        frame_id=frame_id_value,
    )
