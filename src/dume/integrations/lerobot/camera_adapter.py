"""Placeholder boundary for future LeRobot camera adapters.

This module intentionally does not import LeRobot. A future adapter should wrap
an existing LeRobot camera object behind the ``FrameSource`` protocol instead of
duplicating LeRobot connection and cleanup behavior here.
"""

from core.types import FrameSource


def create_lerobot_source(**_kwargs: object) -> FrameSource:
    raise NotImplementedError(
        "LeRobot camera integration is not available in this repository yet. "
        "Use backend='fake', 'webcam', or 'realsense', or add a thin adapter "
        "around an existing LeRobot camera class."
    )
