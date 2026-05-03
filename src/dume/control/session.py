from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from dume.config import (
    CalibrationConfig,
    HardwareConfig,
    PoseLibrary,
    ProjectPaths,
    WorkspaceConfig,
    default_calibration_config,
    default_hardware_config,
    default_pose_library,
    default_workspace_config,
    load_calibration_config,
    load_hardware_config,
    load_pose_library,
    load_workspace_config,
    save_calibration_config,
    save_hardware_config,
    save_pose_library,
    save_workspace_config,
)


@dataclass
class ControlSession:
    paths: ProjectPaths
    hardware: HardwareConfig
    calibration: CalibrationConfig
    workspace: WorkspaceConfig
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

        if paths.workspace_config.exists():
            workspace = load_workspace_config(paths.workspace_config)
        else:
            workspace = default_workspace_config()
            save_workspace_config(paths.workspace_config, workspace)

        if paths.poses_file.exists():
            poses = load_pose_library(paths.poses_file)
        else:
            poses = default_pose_library(len(hardware.motors))
            save_pose_library(paths.poses_file, poses)

        return cls(
            paths=paths,
            hardware=hardware,
            calibration=calibration,
            workspace=workspace,
            poses=poses,
        )

    def bootstrap(self) -> None:
        self.paths.ensure_directories()
        self.save_all()

    def save_all(self) -> None:
        save_hardware_config(self.paths.hardware_config, self.hardware)
        save_calibration_config(self.paths.calibration_config, self.calibration)
        save_workspace_config(self.paths.workspace_config, self.workspace)
        save_pose_library(self.paths.poses_file, self.poses)

    def save_hardware(self) -> None:
        save_hardware_config(self.paths.hardware_config, self.hardware)

    def save_calibration(self) -> None:
        save_calibration_config(self.paths.calibration_config, self.calibration)

    def save_workspace(self) -> None:
        save_workspace_config(self.paths.workspace_config, self.workspace)

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
            "bin_position_count": len(self.workspace.bin_positions),
            "loadout_capacity": self.workspace.loadout_area.capacity,
            "pose_count": len(self.poses.poses),
            "motion_count": motion_count,
        }
