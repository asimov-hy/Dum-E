from perception.filters import CooldownFilter
from perception.types import GestureObservation, GestureSource, GestureType


def test_same_key_is_suppressed_within_cooldown_window() -> None:
    cooldown = CooldownFilter(cooldown_seconds=1.0)

    first = cooldown.apply([_observation(timestamp_ms=1000)], timestamp_ms=1000)
    second = cooldown.apply([_observation(timestamp_ms=1500)], timestamp_ms=1500)

    assert [obs.type for obs in first] == [GestureType.THUMBS_UP]
    assert second == []
    assert cooldown.last_suppressed_count == 1


def test_same_key_is_allowed_after_cooldown_expires() -> None:
    cooldown = CooldownFilter(cooldown_seconds=1.0)

    cooldown.apply([_observation(timestamp_ms=1000)], timestamp_ms=1000)
    emitted = cooldown.apply([_observation(timestamp_ms=2100)], timestamp_ms=2100)

    assert [obs.type for obs in emitted] == [GestureType.THUMBS_UP]


def test_different_keys_cool_down_independently() -> None:
    cooldown = CooldownFilter(cooldown_seconds=1.0)

    cooldown.apply([_observation(timestamp_ms=1000)], timestamp_ms=1000)
    emitted = cooldown.apply(
        [_observation(GestureType.PALM, timestamp_ms=1100)],
        timestamp_ms=1100,
    )

    assert [obs.type for obs in emitted] == [GestureType.PALM]


def test_boundary_allows_when_elapsed_equals_cooldown() -> None:
    cooldown = CooldownFilter(cooldown_seconds=1.0)

    cooldown.apply([_observation(timestamp_ms=1000)], timestamp_ms=1000)
    emitted = cooldown.apply([_observation(timestamp_ms=2000)], timestamp_ms=2000)

    assert [obs.type for obs in emitted] == [GestureType.THUMBS_UP]


def test_cooldown_is_deterministic_with_synthetic_timestamps() -> None:
    cooldown = CooldownFilter(cooldown_seconds=0.25)

    cooldown.apply([_observation(timestamp_ms=100)], timestamp_ms=100)
    suppressed = cooldown.apply([_observation(timestamp_ms=349)], timestamp_ms=349)
    emitted = cooldown.apply([_observation(timestamp_ms=350)], timestamp_ms=350)

    assert suppressed == []
    assert [obs.type for obs in emitted] == [GestureType.THUMBS_UP]


def _observation(
    gesture_type: GestureType = GestureType.THUMBS_UP,
    *,
    timestamp_ms: int,
) -> GestureObservation:
    return GestureObservation(
        type=gesture_type,
        confidence=0.9,
        source=GestureSource.GEOMETRY,
        timestamp_ms=timestamp_ms,
        handedness="Right",
        hand_index=0,
        raw_label=gesture_type.name,
        raw_label_confidence=0.9,
        camera_name="unit-test",
        frame_id=timestamp_ms,
    )
