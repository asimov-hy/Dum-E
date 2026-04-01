from __future__ import annotations

import re
from pathlib import Path

from dume.config import MotionDefinition, MotionStep, load_motion_definition, save_motion_definition
from dume.control.session import ControlSession

ASSET_NAME_RE = re.compile(r"^[a-z0-9_]+$")


def validate_asset_name(name: str) -> str:
    if not ASSET_NAME_RE.fullmatch(name):
        raise ValueError("Names must use lowercase snake_case")
    return name


class PoseStore:
    """Stores named poses and motion skeletons on disk."""

    def __init__(self, session: ControlSession) -> None:
        self.session = session

    def save_pose(self, name: str, joints: list[float]) -> None:
        validated_name = validate_asset_name(name)
        self.session.poses.poses[validated_name] = joints
        self.session.save_poses()

    def list_poses(self) -> dict[str, list[float]]:
        return dict(sorted(self.session.poses.poses.items()))

    def load_pose(self, name: str) -> list[float]:
        try:
            return self.session.poses.poses[name]
        except KeyError as exc:
            raise ValueError(f"Unknown pose: {name}") from exc

    def scaffold_motion(self, name: str, pose_names: list[str]) -> MotionDefinition:
        validated_name = validate_asset_name(name)
        if not pose_names:
            raise ValueError("At least one pose is required to scaffold a motion")
        steps: list[MotionStep] = []
        for pose_name in pose_names:
            validate_asset_name(pose_name)
            if pose_name not in self.session.poses.poses:
                raise ValueError(f"Unknown pose: {pose_name}")
            steps.append(MotionStep(pose=pose_name, duration_s=1.0, hold_s=0.0))
        motion = MotionDefinition(name=validated_name, steps=steps)
        save_motion_definition(self.motion_path(validated_name), motion)
        return motion

    def list_motions(self) -> list[str]:
        motion_names = [path.stem for path in self.session.paths.motions_dir.glob("*.json")]
        return sorted(motion_names)

    def load_motion(self, name: str) -> MotionDefinition:
        validated_name = validate_asset_name(name)
        path = self.motion_path(validated_name)
        if not path.exists():
            raise ValueError(f"Unknown motion: {validated_name}")
        return load_motion_definition(path)

    def motion_path(self, name: str) -> Path:
        return self.session.paths.motions_dir / f"{name}.json"
