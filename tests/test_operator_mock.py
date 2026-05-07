import numpy as np

from core.frame import Frame
from perception.gesture import GestureService
from perception.operator import MockOperatorDetector, OperatorDetector
from perception.types import OperatorPresence


def test_mock_operator_detector_structurally_satisfies_protocol() -> None:
    assert isinstance(MockOperatorDetector(), OperatorDetector)


def test_mock_operator_detector_returns_present_operator_presence() -> None:
    presence = MockOperatorDetector().detect(_frame())

    assert isinstance(presence, OperatorPresence)
    assert presence.present is True
    assert presence.confidence == 1.0
    assert presence.bbox_xyxy is None


def test_operator_detection_is_not_embedded_inside_gesture_service() -> None:
    assert not hasattr(GestureService, "detect_operator")
    assert "operator" not in vars(GestureService)


def _frame() -> Frame:
    return Frame(
        rgb=np.zeros((2, 2, 3), dtype=np.uint8),
        timestamp_ms=100,
        frame_id=1,
        camera_name="unit-test",
    )
