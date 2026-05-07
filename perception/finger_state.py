"""Image-space finger-state detection for Phase 3 geometry mapping."""

from core.landmarks import Landmark2D, Landmark3D
from perception.types import FingerState, FingerStateResult


class FingerStateDetector:
    """Detect extended fingers from normalized image-space hand landmarks.

    v1 uses simple image-space tip-vs-PIP comparisons. Image y increases
    downward, so non-thumb fingers are extended when fingertip.y < pip.y.

    ``world_landmarks`` are accepted for API stability and future geometry work,
    but v1 intentionally does not use them as a replacement for image-space
    comparisons. ``confidence`` is intentionally ``None`` because this heuristic
    is not calibrated; the mapper falls back to ``GestureConfig`` for geometry
    confidence. Per-finger raw margins are populated for debugging.
    """

    _MIN_LANDMARKS = 21

    def detect(
        self,
        landmarks: tuple[Landmark2D, ...],
        world_landmarks: tuple[Landmark3D, ...] | None,
        handedness: str | None,
    ) -> FingerStateResult:
        del world_landmarks
        if len(landmarks) < self._MIN_LANDMARKS:
            raise ValueError(
                f"Expected at least {self._MIN_LANDMARKS} hand landmarks, "
                f"got {len(landmarks)}"
            )

        margins = {
            "thumb": self._thumb_margin(landmarks, handedness),
            "index": self._vertical_margin(landmarks, tip_index=8, pip_index=6),
            "middle": self._vertical_margin(landmarks, tip_index=12, pip_index=10),
            "ring": self._vertical_margin(landmarks, tip_index=16, pip_index=14),
            "pinky": self._vertical_margin(landmarks, tip_index=20, pip_index=18),
        }
        state = FingerState(
            thumb=margins["thumb"] > 0.0,
            index=margins["index"] > 0.0,
            middle=margins["middle"] > 0.0,
            ring=margins["ring"] > 0.0,
            pinky=margins["pinky"] > 0.0,
        )
        return FingerStateResult(state=state, confidence=None, margins=margins)

    def _vertical_margin(
        self,
        landmarks: tuple[Landmark2D, ...],
        *,
        tip_index: int,
        pip_index: int,
    ) -> float:
        return landmarks[pip_index].y - landmarks[tip_index].y

    def _thumb_margin(
        self,
        landmarks: tuple[Landmark2D, ...],
        handedness: str | None,
    ) -> float:
        thumb_tip = landmarks[4]
        thumb_ip = landmarks[3]
        normalized = (handedness or "").strip().lower()
        if normalized == "left":
            return thumb_ip.x - thumb_tip.x
        if normalized == "right":
            return thumb_tip.x - thumb_ip.x

        # Conservative unknown-hand policy: never classify thumb as extended.
        return -abs(thumb_tip.x - thumb_ip.x)
