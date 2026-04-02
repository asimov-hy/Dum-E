from __future__ import annotations

from dum_e.config import CalibrationConfig, JointCalibration
from dum_e.control.arm import ArmController, CENTER_POSITION, STEPS_PER_DEG
from dum_e.control.session import ControlSession


class CalibrationService:
    """Calibration metadata management and guided hardware calibration."""

    def __init__(self, session: ControlSession) -> None:
        self.session = session

    def sync_from_hardware(self) -> CalibrationConfig:
        """Rebuild calibration joint list from hardware config, preserving existing values."""
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

    def run_guided(self, arm: ArmController) -> CalibrationConfig:
        """Interactive guided calibration: walk operator through each joint's limits and home."""
        print("=== Guided Calibration ===")
        print("For each joint you will move it by hand to record limits and home position.")
        print("Torque will be disabled on the active joint so you can move it freely.\n")

        joints: list[JointCalibration] = []

        for motor in self.session.hardware.motors:
            print(f"--- {motor.name} (ID {motor.motor_id}) ---")

            # Disable torque on this joint so operator can back-drive it
            arm.bus.set_torque(motor.motor_id, False)

            input(f"  Move {motor.name} to its MINIMUM limit, then press Enter...")
            min_raw = arm.bus.read_position(motor.motor_id)
            min_deg = round((min_raw - CENTER_POSITION) / STEPS_PER_DEG, 2)
            print(f"  Recorded min: {min_deg} deg (raw {min_raw})")

            input(f"  Move {motor.name} to its MAXIMUM limit, then press Enter...")
            max_raw = arm.bus.read_position(motor.motor_id)
            max_deg = round((max_raw - CENTER_POSITION) / STEPS_PER_DEG, 2)
            print(f"  Recorded max: {max_deg} deg (raw {max_raw})")

            input(f"  Move {motor.name} to its HOME position, then press Enter...")
            home_raw = arm.bus.read_position(motor.motor_id)
            offset_deg = round((home_raw - CENTER_POSITION) / STEPS_PER_DEG, 2)
            print(f"  Recorded home offset: {offset_deg} deg (raw {home_raw})")

            # Re-enable torque to hold position
            arm.bus.set_torque(motor.motor_id, True)

            lo = round(min(min_deg, max_deg), 2)
            hi = round(max(min_deg, max_deg), 2)
            joints.append(
                JointCalibration(
                    motor_name=motor.name,
                    offset_deg=offset_deg,
                    inverted=False,
                    min_deg=lo,
                    max_deg=hi,
                )
            )
            print()

        self.session.calibration = CalibrationConfig(home_pose="home", joints=joints)
        self.session.save_calibration()
        print("Calibration saved.")
        return self.session.calibration
