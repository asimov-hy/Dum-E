from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ArmController:
    """Small interface placeholder for future LeRobot integration."""

    connected: bool = False
    last_joint_command: list[float] = field(default_factory=list)

    def connect(self) -> None:
        self.connected = True

    def move_joints(self, joints: list[float]) -> None:
        self.last_joint_command = joints

    def read_joints(self) -> list[float]:
        return list(self.last_joint_command)
