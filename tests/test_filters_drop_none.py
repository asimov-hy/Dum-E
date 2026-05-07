import numpy as np

from core.frame import Frame
from perception.filters import DropNoneFilter, FilterChain, observations_to_events
from perception.types import FilterConfig, GestureObservation, GestureSource, GestureType


def test_none_observations_are_dropped() -> None:
    observations = [
        _observation(gesture_type=GestureType.NONE),
        _observation(gesture_type=GestureType.PALM),
    ]

    filtered = DropNoneFilter().apply(observations)

    assert [obs.type for obs in filtered] == [GestureType.PALM]


def test_target_gestures_pass_through() -> None:
    observations = [
        _observation(gesture_type=GestureType.THUMBS_UP),
        _observation(gesture_type=GestureType.FIST),
    ]

    filtered = DropNoneFilter().apply(observations)

    assert filtered == observations


def test_none_observations_never_become_events() -> None:
    observations = [
        _observation(gesture_type=GestureType.NONE),
        _observation(gesture_type=GestureType.THUMBS_UP),
    ]

    events = observations_to_events(DropNoneFilter().apply(observations))

    assert [event.type for event in events] == [GestureType.THUMBS_UP]
    assert all(event.type is not GestureType.NONE for event in events)


def test_stable_high_confidence_none_pose_emits_no_events() -> None:
    chain = FilterChain(
        FilterConfig(min_confidence=0.5, stability_frames=3, cooldown_seconds=0.0)
    )
    emitted = []

    for timestamp_ms in range(100, 1100, 100):
        emitted.extend(
            chain.apply(
                [
                    _observation(
                        gesture_type=GestureType.NONE,
                        timestamp_ms=timestamp_ms,
                        raw_label="Thumb_Down",
                    )
                ],
                frame=_frame(timestamp_ms),
            )
        )

    assert emitted == []


def test_dropped_none_observations_do_not_advance_stability() -> None:
    chain = FilterChain(
        FilterConfig(min_confidence=0.5, stability_frames=2, cooldown_seconds=0.0)
    )

    assert chain.apply(
        [_observation(gesture_type=GestureType.NONE, timestamp_ms=100)],
        frame=_frame(100),
    ) == []
    assert chain.apply([_observation(timestamp_ms=200)], frame=_frame(200)) == []
    events = chain.apply([_observation(timestamp_ms=300)], frame=_frame(300))

    assert [event.type for event in events] == [GestureType.THUMBS_UP]


def _frame(timestamp_ms: int) -> Frame:
    return Frame(
        rgb=np.zeros((2, 2, 3), dtype=np.uint8),
        timestamp_ms=timestamp_ms,
        frame_id=timestamp_ms,
        camera_name="unit-test",
    )


def _observation(
    *,
    timestamp_ms: int = 100,
    gesture_type: GestureType = GestureType.THUMBS_UP,
    confidence: float = 0.9,
    raw_label: str | None = "Thumb_Up",
) -> GestureObservation:
    return GestureObservation(
        type=gesture_type,
        confidence=confidence,
        source=GestureSource.GEOMETRY,
        timestamp_ms=timestamp_ms,
        handedness="Right",
        hand_index=0,
        raw_label=raw_label,
        raw_label_confidence=confidence,
        camera_name="unit-test",
        frame_id=timestamp_ms,
    )
