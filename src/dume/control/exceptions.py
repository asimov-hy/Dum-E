from __future__ import annotations


class DumeControlError(Exception):
    """Base exception for control-layer failures."""


class ArmDriverError(DumeControlError):
    """Base exception for arm driver failures."""


class ArmConnectionError(ArmDriverError):
    """Raised when an arm command requires a missing connection."""


class ArmCommandError(ArmDriverError):
    """Raised when an arm command is invalid or rejected."""


class MotionExecutionError(DumeControlError):
    """Raised when a saved motion cannot complete."""
