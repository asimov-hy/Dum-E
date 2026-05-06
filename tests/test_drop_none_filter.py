from perception.filters import DropNoneFilter, observations_to_events
from perception.types import GestureObservation, GestureSource, GestureType


def _observation(gesture_type: GestureType) -> GestureObservation:
    return GestureObservation(
        type=gesture_type,
        confidence=0.9,
        source=GestureSource.CANNED,
        timestamp_ms=100,
        handedness="Right",
        hand_index=0,
        raw_label=gesture_type.value,
        raw_label_confidence=0.9,
        camera_name="test-camera",
        frame_id=3,
    )


def test_none_observations_are_dropped() -> None:
    observations = [
        _observation(GestureType.NONE),
        _observation(GestureType.THUMBS_UP),
    ]

    filtered = DropNoneFilter().apply(observations)

    assert [obs.type for obs in filtered] == [GestureType.THUMBS_UP]


def test_target_gestures_pass_through_and_convert_to_events() -> None:
    observations = [
        _observation(GestureType.THUMBS_UP),
        _observation(GestureType.PALM),
        _observation(GestureType.FIST),
    ]

    events = observations_to_events(DropNoneFilter().apply(observations))

    assert [event.type for event in events] == [
        GestureType.THUMBS_UP,
        GestureType.PALM,
        GestureType.FIST,
    ]
    assert all(event.source is GestureSource.CANNED for event in events)
    assert all(event.camera_name == "test-camera" for event in events)


def test_no_gesture_event_has_none_type() -> None:
    observations = [
        _observation(GestureType.NONE),
        _observation(GestureType.FIST),
    ]

    events = observations_to_events(DropNoneFilter().apply(observations))

    assert events
    assert all(event.type is not GestureType.NONE for event in events)
