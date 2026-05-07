import numpy as np

from core.frame import Frame
from perception.filters import ConfidenceFilter, FilterChain
from perception.types import FilterConfig, GestureObservation, GestureSource, GestureType


def test_low_confidence_observations_are_dropped() -> None:
    observations = [
        _observation(confidence=0.49),
        _observation(confidence=0.75),
    ]

    filtered = ConfidenceFilter(min_confidence=0.5).apply(observations)

    assert [obs.confidence for obs in filtered] == [0.75]


def test_observations_above_threshold_pass() -> None:
    observation = _observation(confidence=0.8)

    filtered = ConfidenceFilter(min_confidence=0.5).apply([observation])

    assert filtered == [observation]


def test_observations_equal_to_threshold_pass() -> None:
    observation = _observation(confidence=0.5)

    filtered = ConfidenceFilter(min_confidence=0.5).apply([observation])

    assert filtered == [observation]


def test_dropped_low_confidence_observations_do_not_advance_stability() -> None:
    chain = FilterChain(
        FilterConfig(min_confidence=0.5, stability_frames=2, cooldown_seconds=0.0)
    )

    assert chain.apply([_observation(timestamp_ms=100, confidence=0.4)], frame=_frame(100)) == []
    assert chain.apply([_observation(timestamp_ms=200, confidence=0.9)], frame=_frame(200)) == []
    events = chain.apply([_observation(timestamp_ms=300, confidence=0.9)], frame=_frame(300))

    assert [event.type for event in events] == [GestureType.THUMBS_UP]


def test_confidence_filter_requires_no_camera_or_mediapipe() -> None:
    filtered = ConfidenceFilter(min_confidence=0.9).apply([_observation(confidence=0.1)])

    assert filtered == []


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
    confidence: float = 0.9,
    gesture_type: GestureType = GestureType.THUMBS_UP,
) -> GestureObservation:
    return GestureObservation(
        type=gesture_type,
        confidence=confidence,
        source=GestureSource.CANNED,
        timestamp_ms=timestamp_ms,
        handedness="Right",
        hand_index=0,
        raw_label="Thumb_Up",
        raw_label_confidence=confidence,
        camera_name="unit-test",
        frame_id=timestamp_ms,
    )
