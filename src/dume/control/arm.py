from __future__ import annotations

from abc import ABC, abstractmethod

from dume.control.exceptions import ConnectionError, JointLimitError


class ArmDriver(ABC):
    """Interface for robot arm drivers.

    Real hardware drivers, simulators, and tests should satisfy this contract so
    replay and autonomy code do not depend on one transport implementation.
    """

    @abstractmethod
    def connect(self) -> None:
        """Open the driver connection."""

    @abstractmethod
    def disconnect(self) -> None:
        """Close the driver connection."""

    @abstractmethod
    def move_joints(self, joints: list[float], speed: float = 0.5) -> bool:
        """Move to joint targets and return whether the command completed."""

    @abstractmethod
    def read_joints(self) -> list[float]:
        """Return the latest known joint positions."""

    @abstractmethod
    def is_connected(self) -> bool:
        """Return whether the driver is connected."""


class MockArmDriver(ArmDriver):
    """In-memory arm driver for tests and hardware-free development."""

    def __init__(self) -> None:
        self._connected = False
        self._joints: list[float] = []
        self.last_speed = 0.5

    def connect(self) -> None:
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def move_joints(self, joints: list[float], speed: float = 0.5) -> bool:
        if not self._connected:
            raise ConnectionError("Arm driver is not connected")
        if not joints:
            raise JointLimitError("Joint target must include at least one value")
        self._joints = list(joints)
        self.last_speed = speed
        return True

    def read_joints(self) -> list[float]:
        if not self._connected:
            raise ConnectionError("Arm driver is not connected")
        return list(self._joints)

    def is_connected(self) -> bool:
        return self._connected
