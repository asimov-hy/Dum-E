"""Phase 4 gesture filter chain.

The command-event path is:

1. confidence
2. drop NONE
3. stability
4. cooldown

One ``FilterChain.apply`` call represents exactly one frame.
"""

from collections.abc import Sequence
from typing import TypeAlias

from core.frame import Frame
from perception.types import FilterConfig, GestureEvent, GestureObservation, GestureType


StabilityKey: TypeAlias = tuple[GestureType, str | None, str | None]


class ConfidenceFilter:
    """Drop observations below the configured confidence threshold."""

    def __init__(self, min_confidence: float) -> None:
        self.min_confidence = min_confidence

    def apply(
        self,
        observations: Sequence[GestureObservation],
    ) -> list[GestureObservation]:
        """Return observations whose confidence is at or above the threshold."""

        return [obs for obs in observations if obs.confidence >= self.min_confidence]


class DropNoneFilter:
    """Remove rejection-class observations from command-event output."""

    def apply(
        self,
        observations: Sequence[GestureObservation],
    ) -> list[GestureObservation]:
        return [obs for obs in observations if obs.type is not GestureType.NONE]


class StabilityFilter:
    """Require a mapped gesture key to appear in consecutive frames.

    The key is exactly ``(type, handedness, camera_name)``. It intentionally
    excludes raw labels, finger counts, hand index, frame ID, and finger state
    so classifier-label flicker does not break an otherwise stable mapped pose.
    """

    def __init__(self, stability_frames: int) -> None:
        if stability_frames < 1:
            raise ValueError("stability_frames must be at least 1")
        self.stability_frames = stability_frames
        self._counts: dict[StabilityKey, int] = {}

    @property
    def counts(self) -> dict[StabilityKey, int]:
        return dict(self._counts)

    def apply(
        self,
        observations: Sequence[GestureObservation],
    ) -> list[GestureObservation]:
        """Advance stability state for exactly one frame."""

        current_by_key = {_stability_key(obs): obs for obs in observations}
        next_counts: dict[StabilityKey, int] = {}
        stable: list[GestureObservation] = []

        for key, obs in current_by_key.items():
            count = self._counts.get(key, 0) + 1
            next_counts[key] = count
            if count >= self.stability_frames:
                stable.append(obs)

        # Keys absent from this frame are reset. Empty observations reset all.
        self._counts = next_counts
        return stable


class CooldownFilter:
    """Suppress repeated events for the same stability key.

    Cooldown uses deterministic frame/event timestamps. A key is allowed again
    when ``elapsed_ms >= cooldown_seconds * 1000``.
    """

    def __init__(self, cooldown_seconds: float) -> None:
        if cooldown_seconds < 0:
            raise ValueError("cooldown_seconds must not be negative")
        self.cooldown_ms = cooldown_seconds * 1000.0
        self._last_emitted_ms: dict[StabilityKey, int] = {}
        self.last_suppressed_count = 0

    def apply(
        self,
        observations: Sequence[GestureObservation],
        *,
        timestamp_ms: int,
    ) -> list[GestureObservation]:
        passed: list[GestureObservation] = []
        suppressed = 0

        for obs in observations:
            key = _stability_key(obs)
            previous_ms = self._last_emitted_ms.get(key)
            if previous_ms is None or timestamp_ms - previous_ms >= self.cooldown_ms:
                self._last_emitted_ms[key] = timestamp_ms
                passed.append(obs)
            else:
                suppressed += 1

        self.last_suppressed_count = suppressed
        return passed


class FilterChain:
    """Apply Phase 4 filters and convert survivors into command events.

    Observation/frame validation treats ``frame_id=None`` as unknown. If both
    observation and frame carry a frame ID, they must match; if either is
    ``None``, the ID check is skipped.
    """

    def __init__(self, config: FilterConfig | None = None) -> None:
        self.config = config or FilterConfig()
        self._confidence = ConfidenceFilter(self.config.min_confidence)
        self._drop_none = DropNoneFilter()
        self._stability = StabilityFilter(self.config.stability_frames)
        self._cooldown = CooldownFilter(self.config.cooldown_seconds)
        self.last_debug: dict[str, object] = {}

    def apply(
        self,
        observations: Sequence[GestureObservation],
        *,
        frame: Frame,
    ) -> list[GestureEvent]:
        """Apply the full filter chain for one frame."""

        self._validate_frame_boundary(observations, frame)

        after_confidence = self._confidence.apply(observations)
        after_none = self._drop_none.apply(after_confidence)
        after_stability = self._stability.apply(after_none)
        after_cooldown = self._cooldown.apply(
            after_stability,
            timestamp_ms=frame.timestamp_ms,
        )

        self.last_debug = {
            "input_count": len(observations),
            "confidence_pass_count": len(after_confidence),
            "confidence_drop_count": len(observations) - len(after_confidence),
            "none_drop_count": len(after_confidence) - len(after_none),
            "stability_pass_count": len(after_stability),
            "stability_required_frames": self.config.stability_frames,
            "stability_counts": {
                _format_key(key): count for key, count in self._stability.counts.items()
            },
            "cooldown_pass_count": len(after_cooldown),
            "cooldown_drop_count": self._cooldown.last_suppressed_count,
            "emitted_count": len(after_cooldown),
        }
        return observations_to_events(after_cooldown)

    def _validate_frame_boundary(
        self,
        observations: Sequence[GestureObservation],
        frame: Frame,
    ) -> None:
        for obs in observations:
            if obs.timestamp_ms != frame.timestamp_ms:
                raise ValueError(
                    "Observation timestamp_ms does not match supplied frame: "
                    f"{obs.timestamp_ms} != {frame.timestamp_ms}"
                )
            if obs.camera_name != frame.camera_name:
                raise ValueError(
                    "Observation camera_name does not match supplied frame: "
                    f"{obs.camera_name!r} != {frame.camera_name!r}"
                )
            if (
                obs.frame_id is not None
                and frame.frame_id is not None
                and obs.frame_id != frame.frame_id
            ):
                raise ValueError(
                    "Observation frame_id does not match supplied frame: "
                    f"{obs.frame_id} != {frame.frame_id}"
                )


def observations_to_events(
    observations: Sequence[GestureObservation],
) -> list[GestureEvent]:
    """Convert command-relevant observations into events.

    ``GestureType.NONE`` is rejected here as a final guard, so it can remain
    visible in observations without ever becoming a command event.
    """

    events: list[GestureEvent] = []
    for obs in observations:
        if obs.type is GestureType.NONE:
            continue
        events.append(
            GestureEvent(
                type=obs.type,
                confidence=obs.confidence,
                source=obs.source,
                timestamp_ms=obs.timestamp_ms,
                handedness=obs.handedness,
                hand_index=obs.hand_index,
                finger_count=obs.finger_count,
                finger_state=obs.finger_state,
                raw_label=obs.raw_label,
                raw_label_confidence=obs.raw_label_confidence,
                camera_name=obs.camera_name,
                frame_id=obs.frame_id,
            )
        )
    return events


def _stability_key(obs: GestureObservation) -> StabilityKey:
    return obs.type, obs.handedness, obs.camera_name


def _format_key(key: StabilityKey) -> str:
    gesture_type, handedness, camera_name = key
    return f"{gesture_type.name}:{handedness}:{camera_name}"
