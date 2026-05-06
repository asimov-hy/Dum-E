"""Phase 2 gesture filters.

Only the drop-NONE behavior exists in Phase 2. Confidence, stability, cooldown,
and frame-boundary filtering are intentionally left for later phases.
"""

from collections.abc import Sequence

from perception.types import GestureEvent, GestureObservation, GestureType


class DropNoneFilter:
    """Remove rejection-class observations from command-event output."""

    def apply(
        self,
        observations: Sequence[GestureObservation],
    ) -> list[GestureObservation]:
        return [obs for obs in observations if obs.type is not GestureType.NONE]


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
