import numpy as np

from core.landmarks import Landmark2D
from demos.gesture_demo import draw_overlay
from perception.types import GestureObservation, GestureSource, GestureType


class FakeCV2:
    FONT_HERSHEY_SIMPLEX = 0

    def __init__(self) -> None:
        self.texts: list[str] = []
        self.lines = 0
        self.circles = 0

    def putText(
        self,
        image: np.ndarray,
        text: str,
        origin: tuple[int, int],
        font: int,
        scale: float,
        color: tuple[int, int, int],
        thickness: int,
    ) -> None:
        del image, origin, font, scale, color, thickness
        self.texts.append(text)

    def line(
        self,
        image: np.ndarray,
        start: tuple[int, int],
        end: tuple[int, int],
        color: tuple[int, int, int],
        thickness: int,
    ) -> None:
        del image, start, end, color, thickness
        self.lines += 1

    def circle(
        self,
        image: np.ndarray,
        center: tuple[int, int],
        radius: int,
        color: tuple[int, int, int],
        thickness: int,
    ) -> None:
        del image, center, radius, color, thickness
        self.circles += 1


def test_overlay_renders_landmarks_without_finger_state() -> None:
    cv2 = FakeCV2()
    frame_bgr = np.zeros((120, 160, 3), dtype=np.uint8)
    observation = GestureObservation(
        type=GestureType.THUMBS_UP,
        confidence=0.9,
        source=GestureSource.CANNED,
        timestamp_ms=100,
        handedness="Right",
        hand_index=0,
        landmarks=tuple(Landmark2D(x=i / 20, y=i / 20, z=0.0) for i in range(21)),
        finger_state=None,
        finger_state_result=None,
        finger_count=None,
        raw_label="Thumb_Up",
        raw_label_confidence=0.9,
    )

    rendered = draw_overlay(
        frame_bgr,
        [observation],
        [],
        cv2_module=cv2,
        draw_landmarks=True,
    )

    assert rendered is frame_bgr
    assert cv2.lines > 0
    assert cv2.circles == 21
    assert any("mapped=THUMBS_UP" in text for text in cv2.texts)
    assert any("finger state: not available" in text for text in cv2.texts)
