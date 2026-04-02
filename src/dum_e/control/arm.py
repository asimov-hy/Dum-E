"""Arm controller — high-level joint interface built on a MotorBus."""

from __future__ import annotations

from dataclasses import dataclass, field

from dum_e.config import CalibrationConfig, JointCalibration, MotorConfig
from dum_e.control.bus import MotorBus


# STS3215 constants
STEPS_PER_REVOLUTION = 4096
CENTER_POSITION = 2048
STEPS_PER_DEG = STEPS_PER_REVOLUTION / 360.0


@dataclass
class ArmController:
    """Joint-level arm interface with calibration-aware position conversion."""

    bus: MotorBus
    motors: list[MotorConfig]
    calibration: CalibrationConfig
    _enabled: bool = field(default=False, init=False)

    def connect(self) -> None:
        self.bus.connect()

    def disconnect(self) -> None:
        if self._enabled:
            self.disable()
        self.bus.disconnect()

    @property
    def is_connected(self) -> bool:
        return self.bus.is_connected

    def enable(self) -> None:
        for motor in self.motors:
            self.bus.set_torque(motor.motor_id, True)
        self._enabled = True

    def disable(self) -> None:
        for motor in self.motors:
            self.bus.set_torque(motor.motor_id, False)
        self._enabled = False

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def read_joints(self) -> list[float]:
        """Read all joint positions in degrees."""
        return [
            self._raw_to_deg(self.bus.read_position(m.motor_id), m.name)
            for m in self.motors
        ]

    def move_joints(self, positions_deg: list[float]) -> None:
        """Command all joints to target positions in degrees."""
        if not self._enabled:
            raise RuntimeError("Arm must be enabled before moving")
        if len(positions_deg) != len(self.motors):
            raise ValueError(
                f"Expected {len(self.motors)} joint values, got {len(positions_deg)}"
            )
        for motor, deg in zip(self.motors, positions_deg):
            clamped = self._clamp(deg, motor.name)
            self.bus.write_position(motor.motor_id, self._deg_to_raw(clamped, motor.name))

    def move_joint(self, index: int, position_deg: float) -> None:
        """Command a single joint to a target position in degrees."""
        if not self._enabled:
            raise RuntimeError("Arm must be enabled before moving")
        motor = self.motors[index]
        clamped = self._clamp(position_deg, motor.name)
        self.bus.write_position(motor.motor_id, self._deg_to_raw(clamped, motor.name))

    def jog_joint(self, index: int, delta_deg: float) -> float:
        """Jog a single joint by a delta. Returns new position in degrees."""
        if not self._enabled:
            raise RuntimeError("Arm must be enabled before jogging")
        motor = self.motors[index]
        current_deg = self._raw_to_deg(self.bus.read_position(motor.motor_id), motor.name)
        target_deg = self._clamp(current_deg + delta_deg, motor.name)
        self.bus.write_position(motor.motor_id, self._deg_to_raw(target_deg, motor.name))
        return round(target_deg, 2)

    # -- position conversion ---------------------------------------------------

    def _get_cal(self, motor_name: str) -> JointCalibration | None:
        for joint in self.calibration.joints:
            if joint.motor_name == motor_name:
                return joint
        return None

    def _raw_to_deg(self, raw: int, motor_name: str) -> float:
        deg = (raw - CENTER_POSITION) / STEPS_PER_DEG
        cal = self._get_cal(motor_name)
        if cal:
            if cal.inverted:
                deg = -deg
            deg -= cal.offset_deg
        return round(deg, 2)

    def _deg_to_raw(self, deg: float, motor_name: str) -> int:
        cal = self._get_cal(motor_name)
        if cal:
            deg = deg + cal.offset_deg
            if cal.inverted:
                deg = -deg
        raw = int(deg * STEPS_PER_DEG + CENTER_POSITION)
        return max(0, min(4095, raw))

    def _clamp(self, deg: float, motor_name: str) -> float:
        cal = self._get_cal(motor_name)
        if cal:
            if cal.min_deg is not None:
                deg = max(deg, cal.min_deg)
            if cal.max_deg is not None:
                deg = min(deg, cal.max_deg)
        return deg
