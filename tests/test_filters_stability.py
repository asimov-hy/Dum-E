import numpy as np

from core.frame import Frame
from perception.filters import FilterChain
from perception.types import FilterConfig, GestureObservation, GestureSource, GestureType


def test_three_consecutive_thumbs_up_emits_on_third_frame() -> None:
    events = _run_sequence(
        FilterConfig(stability_frames=3, cooldown_seconds=99.0),
        [
            (100, _observation(timestamp_ms=100)),
            (200, _observation(timestamp_ms=200)),
            (300, _observation(timestamp_ms=300)),
        ],
    )

    assert [(timestamp, event.type) for timestamp, event in events] == [
        (300, GestureType.THUMBS_UP)
    ]


def test_fewer_than_required_frames_emit_no_event() -> None:
    events = _run_sequence(
        FilterConfig(stability_frames=3, cooldown_seconds=0.0),
        [
            (100, _observation(timestamp_ms=100)),
            (200, _observation(timestamp_ms=200)),
        ],
    )

    assert events == []


def test_held_gesture_does_not_duplicate_during_cooldown() -> None:
    sequence = [
        (timestamp_ms, _observation(timestamp_ms=timestamp_ms))
        for timestamp_ms in range(100, 1100, 100)
    ]

    events = _run_sequence(FilterConfig(stability_frames=3, cooldown_seconds=99.0), sequence)

    assert [(timestamp, event.type) for timestamp, event in events] == [
        (300, GestureType.THUMBS_UP)
    ]


def test_empty_frame_resets_two_finger_streak() -> None:
    events = _run_sequence(
        FilterConfig(stability_frames=3, cooldown_seconds=0.0),
        [
            (100, _observation(GestureType.TWO_FINGERS, timestamp_ms=100)),
            (200, _observation(GestureType.TWO_FINGERS, timestamp_ms=200)),
            (300, None),
            (400, _observation(GestureType.TWO_FINGERS, timestamp_ms=400)),
        ],
    )

    assert events == []


def test_confidence_filtered_candidate_does_not_advance_stability() -> None:
    events = _run_sequence(
        FilterConfig(min_confidence=0.5, stability_frames=2, cooldown_seconds=0.0),
        [
            (100, _observation(timestamp_ms=100, confidence=0.1)),
            (200, _observation(timestamp_ms=200, confidence=0.9)),
            (300, _observation(timestamp_ms=300, confidence=0.9)),
        ],
    )

    assert [(timestamp, event.type) for timestamp, event in events] == [
        (300, GestureType.THUMBS_UP)
    ]


def test_low_confidence_palm_for_ten_frames_emits_no_event() -> None:
    sequence = [
        (
            timestamp_ms,
            _observation(
                GestureType.PALM,
                timestamp_ms=timestamp_ms,
                confidence=0.1,
                raw_label="Open_Palm",
            ),
        )
        for timestamp_ms in range(100, 1100, 100)
    ]

    events = _run_sequence(
        FilterConfig(min_confidence=0.5, stability_frames=3, cooldown_seconds=0.0),
        sequence,
    )

    assert events == []


def test_none_candidate_does_not_advance_stability() -> None:
    events = _run_sequence(
        FilterConfig(stability_frames=2, cooldown_seconds=0.0),
        [
            (100, _observation(GestureType.NONE, timestamp_ms=100)),
            (200, _observation(timestamp_ms=200)),
            (300, _observation(timestamp_ms=300)),
        ],
    )

    assert [(timestamp, event.type) for timestamp, event in events] == [
        (300, GestureType.THUMBS_UP)
    ]


def test_raw_label_flicker_does_not_reset_stable_mapped_type() -> None:
    events = _run_sequence(
        FilterConfig(stability_frames=3, cooldown_seconds=0.0),
        [
            (
                100,
                _observation(
                    GestureType.TWO_FINGERS,
                    timestamp_ms=100,
                    raw_label="Victory",
                ),
            ),
            (
                200,
                _observation(
                    GestureType.TWO_FINGERS,
                    timestamp_ms=200,
                    raw_label=None,
                ),
            ),
            (
                300,
                _observation(
                    GestureType.TWO_FINGERS,
                    timestamp_ms=300,
                    raw_label="Victory",
                ),
            ),
        ],
    )

    assert [(timestamp, event.type) for timestamp, event in events] == [
        (300, GestureType.TWO_FINGERS)
    ]


def test_palm_then_fist_use_independent_keys() -> None:
    events = _run_sequence(
        FilterConfig(stability_frames=2, cooldown_seconds=0.0),
        [
            (100, _observation(GestureType.PALM, timestamp_ms=100)),
            (200, _observation(GestureType.PALM, timestamp_ms=200)),
            (300, _observation(GestureType.FIST, timestamp_ms=300)),
            (400, _observation(GestureType.FIST, timestamp_ms=400)),
        ],
    )

    assert [(timestamp, event.type) for timestamp, event in events] == [
        (200, GestureType.PALM),
        (400, GestureType.FIST),
    ]


def test_stability_key_excludes_finger_count() -> None:
    events = _run_sequence(
        FilterConfig(stability_frames=3, cooldown_seconds=0.0),
        [
            (100, _observation(timestamp_ms=100, finger_count=1)),
            (200, _observation(timestamp_ms=200, finger_count=99)),
            (300, _observation(timestamp_ms=300, finger_count=1)),
        ],
    )

    assert [(timestamp, event.type) for timestamp, event in events] == [
        (300, GestureType.THUMBS_UP)
    ]


def _run_sequence(
    config: FilterConfig,
    sequence: list[tuple[int, GestureObservation | None]],
) -> list[tuple[int, object]]:
    chain = FilterChain(config)
    events = []
    for timestamp_ms, observation in sequence:
        observations = [] if observation is None else [observation]
        for event in chain.apply(observations, frame=_frame(timestamp_ms)):
            events.append((timestamp_ms, event))
    return events


def _frame(timestamp_ms: int) -> Frame:
    return Frame(
        rgb=np.zeros((2, 2, 3), dtype=np.uint8),
        timestamp_ms=timestamp_ms,
        frame_id=timestamp_ms,
        camera_name="unit-test",
    )


def _observation(
    gesture_type: GestureType = GestureType.THUMBS_UP,
    *,
    timestamp_ms: int,
    confidence: float = 0.9,
    raw_label: str | None = "Thumb_Up",
    finger_count: int | None = None,
) -> GestureObservation:
    return GestureObservation(
        type=gesture_type,
        confidence=confidence,
        source=GestureSource.GEOMETRY,
        timestamp_ms=timestamp_ms,
        handedness="Right",
        hand_index=0,
        finger_count=finger_count,
        raw_label=raw_label,
        raw_label_confidence=confidence,
        camera_name="unit-test",
        frame_id=timestamp_ms,
    )
