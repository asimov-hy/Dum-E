from __future__ import annotations

from dume.config import CalibrationConfig, JointCalibration
from dume.control.session import ControlSession


class CalibrationService:
    """Owns saved calibration metadata, independent from hardware execution."""

    def __init__(self, session: ControlSession) -> None:
        self.session = session

    def sync_from_hardware(self) -> CalibrationConfig:
        existing = {joint.motor_name: joint for joint in self.session.calibration.joints}
        ordered: list[JointCalibration] = []
        for motor in self.session.hardware.motors:
            ordered.append(existing.get(motor.name, JointCalibration(motor_name=motor.name)))
        self.session.calibration = CalibrationConfig(
            home_pose=self.session.calibration.home_pose,
            joints=ordered,
        )
        self.session.save_calibration()
        return self.session.calibration

    def current(self) -> CalibrationConfig:
        return self.session.calibration
