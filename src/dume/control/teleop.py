from __future__ import annotations

from abc import ABC, abstractmethod


class TeleopDriver(ABC):
    """Interface for operator teleoperation inputs."""

    @abstractmethod
    def start(self) -> None:
        """Start reading operator input."""

    @abstractmethod
    def stop(self) -> None:
        """Stop reading operator input."""

    @abstractmethod
    def is_active(self) -> bool:
        """Return whether teleoperation input is active."""


class MockTeleopDriver(TeleopDriver):
    """In-memory teleop driver for tests and hardware-free development."""

    def __init__(self) -> None:
        self._active = False

    def start(self) -> None:
        self._active = True

    def stop(self) -> None:
        self._active = False

    def is_active(self) -> bool:
        return self._active


def teleop_status_description() -> str:
    """Return CLI-friendly status text for the planned teleop surface."""

    return (
        "Teleop is not connected to live hardware yet.\n"
        "Planned operator defaults:\n"
        "- low-speed joint jogging\n"
        "- explicit enable/disable flow\n"
        "- named-pose shortcuts\n"
        "- emergency stop binding\n"
        "- optional gamepad support after keyboard jog is stable"
    )
