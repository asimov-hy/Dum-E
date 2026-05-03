from __future__ import annotations


class HardwareError(Exception):
    """Base exception for hardware-control failures."""


class ConnectionError(HardwareError):
    """Raised when hardware access requires a missing connection."""


class MotorStallError(HardwareError):
    """Raised when a motor reports or simulates a stall."""


class JointLimitError(HardwareError):
    """Raised when a joint target is invalid or outside allowed limits."""


class CalibrationError(HardwareError):
    """Raised when calibration data or calibration execution fails."""
