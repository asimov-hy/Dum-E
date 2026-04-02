from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from dum_e.config import (
    CalibrationConfig,
    HardwareConfig,
    PoseLibrary,
    ProjectPaths,
    default_calibration_config,
    default_hardware_config,
    default_pose_library,
    load_calibration_config,
    load_hardware_config,
    load_pose_library,
    save_calibration_config,
    save_hardware_config,
    save_pose_library,
)


@dataclass
class ControlSession:
    paths: ProjectPaths
    hardware: HardwareConfig
    calibration: CalibrationConfig
    poses: PoseLibrary

    @classmethod
    def load(cls, root: Path) -> "ControlSession":
        paths = ProjectPaths.from_root(root)
        paths.ensure_directories()

        if paths.hardware_config.exists():
            hardware = load_hardware_config(paths.hardware_config)
        else:
            hardware = default_hardware_config()
            save_hardware_config(paths.hardware_config, hardware)

        if paths.calibration_config.exists():
            calibration = load_calibration_config(paths.calibration_config)
        else:
            calibration = default_calibration_config(hardware)
            save_calibration_config(paths.calibration_config, calibration)

        if paths.poses_file.exists():
            poses = load_pose_library(paths.poses_file)
        else:
            poses = default_pose_library(len(hardware.motors))
            save_pose_library(paths.poses_file, poses)

        return cls(paths=paths, hardware=hardware, calibration=calibration, poses=poses)

    def bootstrap(self) -> None:
        self.paths.ensure_directories()
        self.save_all()

    def save_all(self) -> None:
        save_hardware_config(self.paths.hardware_config, self.hardware)
        save_calibration_config(self.paths.calibration_config, self.calibration)
        save_pose_library(self.paths.poses_file, self.poses)

    def save_hardware(self) -> None:
        save_hardware_config(self.paths.hardware_config, self.hardware)

    def save_calibration(self) -> None:
        save_calibration_config(self.paths.calibration_config, self.calibration)

    def save_poses(self) -> None:
        save_pose_library(self.paths.poses_file, self.poses)

    def status_summary(self) -> dict[str, int | str]:
        motion_count = len(list(self.paths.motions_dir.glob("*.json")))
        return {
            "robot_name": self.hardware.robot_name,
            "port": self.hardware.serial.port,
            "baudrate": self.hardware.serial.baudrate,
            "motor_count": len(self.hardware.motors),
            "calibration_joint_count": len(self.calibration.joints),
            "pose_count": len(self.poses.poses),
            "motion_count": motion_count,
        }
