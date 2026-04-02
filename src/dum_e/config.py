from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, model_validator


class SerialConfig(BaseModel):
    port: str = "/dev/ttyACM0"
    baudrate: int = 1_000_000


class MotorConfig(BaseModel):
    name: str
    motor_id: int
    model: str = "unknown"
    notes: str | None = None


class HardwareConfig(BaseModel):
    robot_name: str = "so101"
    serial: SerialConfig = Field(default_factory=SerialConfig)
    motors: list[MotorConfig] = Field(default_factory=list)


class JointCalibration(BaseModel):
    motor_name: str
    offset_deg: float = 0.0
    inverted: bool = False
    min_deg: float | None = None
    max_deg: float | None = None


class CalibrationConfig(BaseModel):
    home_pose: str = "home"
    joints: list[JointCalibration] = Field(default_factory=list)


class PoseLibrary(BaseModel):
    poses: dict[str, list[float]] = Field(default_factory=dict)


class MotionStep(BaseModel):
    pose: str | None = None
    joints: list[float] | None = None
    duration_s: float = 1.0
    hold_s: float = 0.0

    @model_validator(mode="after")
    def validate_target(self) -> "MotionStep":
        has_pose = self.pose is not None
        has_joints = self.joints is not None
        if has_pose == has_joints:
            raise ValueError("Each motion step must define exactly one of pose or joints")
        return self


class MotionDefinition(BaseModel):
    name: str
    frame: str = "joint"
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    )
    steps: list[MotionStep] = Field(default_factory=list)


@dataclass(frozen=True)
class ProjectPaths:
    root: Path
    config_dir: Path
    data_dir: Path
    motions_dir: Path
    logs_dir: Path
    hardware_config: Path
    calibration_config: Path
    poses_file: Path

    @classmethod
    def from_root(cls, root: Path) -> "ProjectPaths":
        resolved_root = root.resolve()
        config_dir = resolved_root / "config"
        data_dir = resolved_root / "data"
        motions_dir = data_dir / "motions"
        logs_dir = resolved_root / "logs"
        return cls(
            root=resolved_root,
            config_dir=config_dir,
            data_dir=data_dir,
            motions_dir=motions_dir,
            logs_dir=logs_dir,
            hardware_config=config_dir / "hardware.yaml",
            calibration_config=config_dir / "calibration.yaml",
            poses_file=data_dir / "poses.json",
        )

    def ensure_directories(self) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.motions_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)


def default_hardware_config() -> HardwareConfig:
    return HardwareConfig(
        robot_name="so101",
        motors=[
            MotorConfig(name="shoulder_pan", motor_id=1, model="sts3215"),
            MotorConfig(name="shoulder_lift", motor_id=2, model="sts3215"),
            MotorConfig(name="elbow", motor_id=3, model="sts3215"),
            MotorConfig(name="wrist_pitch", motor_id=4, model="sts3215"),
            MotorConfig(name="wrist_roll", motor_id=5, model="sts3215"),
            MotorConfig(name="gripper", motor_id=6, model="sts3215"),
        ],
    )


def default_calibration_config(hardware: HardwareConfig | None = None) -> CalibrationConfig:
    active_hardware = hardware or default_hardware_config()
    joints = [JointCalibration(motor_name=motor.name) for motor in active_hardware.motors]
    return CalibrationConfig(home_pose="home", joints=joints)


def default_pose_library(joint_count: int = 6) -> PoseLibrary:
    return PoseLibrary(poses={"home": [0.0] * joint_count})


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in YAML file: {path}")
    return data


def save_yaml(path: Path, payload: BaseModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        yaml.safe_dump(payload.model_dump(mode="python"), file, sort_keys=False)


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError(f"Expected object in JSON file: {path}")
    return data


def save_json(path: Path, payload: BaseModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload.model_dump(mode="json"), file, indent=2)
        file.write("\n")


def load_hardware_config(path: Path) -> HardwareConfig:
    return HardwareConfig.model_validate(load_yaml(path))


def save_hardware_config(path: Path, config: HardwareConfig) -> None:
    save_yaml(path, config)


def load_calibration_config(path: Path) -> CalibrationConfig:
    return CalibrationConfig.model_validate(load_yaml(path))


def save_calibration_config(path: Path, config: CalibrationConfig) -> None:
    save_yaml(path, config)


def load_pose_library(path: Path) -> PoseLibrary:
    return PoseLibrary.model_validate(load_json(path))


def save_pose_library(path: Path, library: PoseLibrary) -> None:
    save_json(path, library)


def load_motion_definition(path: Path) -> MotionDefinition:
    return MotionDefinition.model_validate(load_json(path))


def save_motion_definition(path: Path, motion: MotionDefinition) -> None:
    save_json(path, motion)
