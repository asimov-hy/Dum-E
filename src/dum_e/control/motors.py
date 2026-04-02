from __future__ import annotations

from dataclasses import dataclass

from dum_e.config import MotorConfig
from dum_e.control.session import ControlSession


@dataclass
class MotorScanRecord:
    name: str
    expected_id: int
    model: str
    status: str  # "found", "missing", or "configured" (no hardware)


class MotorsService:
    """Motor discovery and ID management."""

    def __init__(self, session: ControlSession) -> None:
        self.session = session

    def scan(self) -> list[MotorScanRecord]:
        """Scan for motors. Uses live ping if arm is connected, else config only."""
        arm = self.session.arm
        records: list[MotorScanRecord] = []
        for motor in self.session.hardware.motors:
            if arm is not None and arm.is_connected:
                found = arm.bus.ping(motor.motor_id)
                status = "found" if found else "missing"
            else:
                status = "configured"
            records.append(
                MotorScanRecord(
                    name=motor.name,
                    expected_id=motor.motor_id,
                    model=motor.model,
                    status=status,
                )
            )
        return records

    def set_motor_id(
        self,
        *,
        name: str | None = None,
        from_id: int | None = None,
        to_id: int,
    ) -> MotorConfig:
        """Update a motor's ID in config and on hardware if connected."""
        motor = self._find_motor(name=name, from_id=from_id)

        if motor.motor_id == to_id:
            return motor

        # Check for ID collisions
        if any(m.motor_id == to_id and m.name != motor.name for m in self.session.hardware.motors):
            raise ValueError(f"Motor ID {to_id} is already assigned")

        # Write to physical motor if connected
        arm = self.session.arm
        if arm is not None and arm.is_connected:
            arm.bus.write_motor_id(motor.motor_id, to_id)

        motor.motor_id = to_id
        self.session.save_hardware()
        return motor

    def _find_motor(self, *, name: str | None, from_id: int | None) -> MotorConfig:
        for motor in self.session.hardware.motors:
            if name is not None and motor.name == name:
                return motor
            if from_id is not None and motor.motor_id == from_id:
                return motor
        if name is not None:
            raise ValueError(f"Unknown motor name: {name}")
        raise ValueError(f"Unknown motor ID: {from_id}")
