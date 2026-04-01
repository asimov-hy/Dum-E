from __future__ import annotations

from dataclasses import dataclass

from dume.config import MotorConfig
from dume.control.session import ControlSession


@dataclass
class MotorScanRecord:
    name: str
    expected_id: int
    model: str
    status: str


class MotorsService:
    """Config-backed motor utilities until live LeRobot transport is attached."""

    def __init__(self, session: ControlSession) -> None:
        self.session = session

    def scan(self) -> list[MotorScanRecord]:
        return [
            MotorScanRecord(
                name=motor.name,
                expected_id=motor.motor_id,
                model=motor.model,
                status="configured",
            )
            for motor in self.session.hardware.motors
        ]

    def set_motor_id(
        self,
        *,
        name: str | None = None,
        from_id: int | None = None,
        to_id: int,
    ) -> MotorConfig:
        for motor in self.session.hardware.motors:
            if name is not None and motor.name == name:
                if motor.motor_id == to_id:
                    return motor
                if any(
                    other.motor_id == to_id and other.name != motor.name
                    for other in self.session.hardware.motors
                ):
                    raise ValueError(f"Motor ID {to_id} is already assigned")
                motor.motor_id = to_id
                self.session.save_hardware()
                return motor
            if from_id is not None and motor.motor_id == from_id:
                if motor.motor_id == to_id:
                    return motor
                if any(
                    other.motor_id == to_id and other.name != motor.name
                    for other in self.session.hardware.motors
                ):
                    raise ValueError(f"Motor ID {to_id} is already assigned")
                motor.motor_id = to_id
                self.session.save_hardware()
                return motor

        if name is not None:
            raise ValueError(f"Unknown motor name: {name}")
        raise ValueError(f"Unknown motor ID: {from_id}")
