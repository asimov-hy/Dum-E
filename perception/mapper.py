"""Phase 2 canned-label gesture mapper."""

from perception.types import GestureSource, GestureType, MappedGesture


class GestureMapper:
    """Map MediaPipe canned labels to the Phase 2 gesture vocabulary."""

    _CANNED_MAP = {
        "Thumb_Up": GestureType.THUMBS_UP,
        "Open_Palm": GestureType.PALM,
        "Closed_Fist": GestureType.FIST,
    }

    def map(
        self,
        *,
        raw_label: str | None,
        raw_confidence: float | None,
        finger_state_result: object | None = None,
    ) -> MappedGesture:
        """Return a canned-label mapping.

        ``finger_state_result`` is accepted for the future mapper API but is
        intentionally ignored in Phase 2.
        """

        del finger_state_result
        gesture_type = self._CANNED_MAP.get(raw_label, GestureType.NONE)
        confidence = raw_confidence if raw_confidence is not None else 0.0
        return MappedGesture(
            type=gesture_type,
            confidence=confidence,
            source=GestureSource.CANNED,
        )
