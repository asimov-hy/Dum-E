"""Gesture mapper combining canned labels and Phase 3 geometry."""

from perception.types import (
    FingerState,
    FingerStateResult,
    GestureConfig,
    GestureSource,
    GestureType,
    MappedGesture,
)


class GestureMapper:
    """Map MediaPipe labels and finger geometry into the gesture vocabulary."""

    _CANNED_MAP = {
        "Thumb_Up": GestureType.THUMBS_UP,
        "Open_Palm": GestureType.PALM,
        "Closed_Fist": GestureType.FIST,
    }

    def __init__(self, config: GestureConfig | None = None) -> None:
        self.config = config or GestureConfig()

    def map(
        self,
        *,
        raw_label: str | None,
        raw_confidence: float | None,
        finger_state_result: FingerStateResult | None = None,
    ) -> MappedGesture:
        """Return a priority-mapped gesture."""

        confidence = float(raw_confidence) if raw_confidence is not None else 0.0
        state = finger_state_result.state if finger_state_result is not None else None
        geometry_confidence = self._geometry_confidence(finger_state_result)

        if self._canned_is_accepted(raw_label, confidence):
            canned_type = self._CANNED_MAP[raw_label]
            if state is not None and self._geometry_agrees(canned_type, state):
                return MappedGesture(
                    type=canned_type,
                    confidence=max(confidence, geometry_confidence),
                    source=GestureSource.HYBRID,
                )
            return MappedGesture(
                type=canned_type,
                confidence=confidence,
                source=GestureSource.CANNED,
            )

        if state is not None:
            geometry_type = self._map_geometry(state)
            if geometry_type is not GestureType.NONE:
                return MappedGesture(
                    type=geometry_type,
                    confidence=geometry_confidence,
                    source=GestureSource.GEOMETRY,
                )
            return MappedGesture(
                type=GestureType.NONE,
                confidence=0.0,
                source=GestureSource.GEOMETRY,
            )

        return MappedGesture(
            type=GestureType.NONE,
            confidence=confidence,
            source=GestureSource.CANNED,
        )

    def _canned_is_accepted(self, raw_label: str | None, confidence: float) -> bool:
        return (
            raw_label in self._CANNED_MAP
            and confidence >= self.config.semantic_threshold
        )

    def _geometry_confidence(
        self,
        finger_state_result: FingerStateResult | None,
    ) -> float:
        if finger_state_result is None or finger_state_result.confidence is None:
            return self.config.default_geometry_confidence
        return finger_state_result.confidence

    def _geometry_agrees(self, gesture_type: GestureType, state: FingerState) -> bool:
        if gesture_type is GestureType.THUMBS_UP:
            return self._is_thumb_only(state)
        if gesture_type is GestureType.FIST:
            return self._is_fist(state)
        if gesture_type is GestureType.PALM:
            return self._is_palm(state)
        return False

    def _map_geometry(self, state: FingerState) -> GestureType:
        if self._is_index_only(state):
            return GestureType.ONE_FINGER
        if self._is_index_middle_only(state):
            return GestureType.TWO_FINGERS
        if self._is_index_middle_ring_only(state):
            return GestureType.THREE_FINGERS
        if self.config.allow_geometry_fist and self._is_fist(state):
            return GestureType.FIST
        if self.config.allow_geometry_palm and self._is_palm(state):
            return GestureType.PALM
        return GestureType.NONE

    def _is_thumb_only(self, state: FingerState) -> bool:
        return state.thumb and not any([state.index, state.middle, state.ring, state.pinky])

    def _is_fist(self, state: FingerState) -> bool:
        return not any([state.thumb, state.index, state.middle, state.ring, state.pinky])

    def _is_palm(self, state: FingerState) -> bool:
        return state.index and state.middle and state.ring and state.pinky

    def _is_index_only(self, state: FingerState) -> bool:
        return (
            not state.thumb
            and state.index
            and not state.middle
            and not state.ring
            and not state.pinky
        )

    def _is_index_middle_only(self, state: FingerState) -> bool:
        return (
            not state.thumb
            and state.index
            and state.middle
            and not state.ring
            and not state.pinky
        )

    def _is_index_middle_ring_only(self, state: FingerState) -> bool:
        return (
            not state.thumb
            and state.index
            and state.middle
            and state.ring
            and not state.pinky
        )
