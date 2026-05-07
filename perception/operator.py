"""Operator-presence boundary for Phase 4.

The operator detector stays separate from gesture recognition so command or
authorization code can decide how to combine operator presence and gestures.
"""

from typing import Protocol, runtime_checkable

from core.frame import Frame
from perception.types import OperatorPresence


@runtime_checkable
class OperatorDetector(Protocol):
    def detect(self, frame: Frame) -> OperatorPresence:
        """Return whether an operator is present in the supplied frame."""


class MockOperatorDetector:
    """Test stub that always reports an operator as present."""

    def detect(self, frame: Frame) -> OperatorPresence:
        del frame
        return OperatorPresence(present=True, confidence=1.0, bbox_xyxy=None)
