from __future__ import annotations

import time

from dum_e.control.arm import ArmController
from dum_e.control.recording import PoseStore
from dum_e.control.session import ControlSession


class ReplayService:
    """Pose and motion replay with optional hardware execution."""

    def __init__(self, session: ControlSession, pose_store: PoseStore) -> None:
        self.session = session
        self.pose_store = pose_store

    # -- inspection (no hardware needed) ---------------------------------------

    def pose_plan(self, name: str) -> str:
        joints = self.pose_store.load_pose(name)
        return f"Replay plan for pose '{name}': {len(joints)} joints -> {joints}"

    def motion_plan(self, name: str) -> str:
        motion = self.pose_store.load_motion(name)
        step_descriptions = []
        for index, step in enumerate(motion.steps, start=1):
            target = step.pose if step.pose is not None else step.joints
            step_descriptions.append(
                f"step {index}: target={target}, duration_s={step.duration_s}, hold_s={step.hold_s}"
            )
        joined_steps = "; ".join(step_descriptions)
        return f"Replay plan for motion '{name}': {joined_steps}"

    # -- execution (requires connected arm) ------------------------------------

    def execute_pose(self, name: str, arm: ArmController) -> list[float]:
        """Move the arm to a saved pose. Returns the target joint values."""
        joints = self.pose_store.load_pose(name)
        arm.move_joints(joints)
        return joints

    def execute_motion(self, name: str, arm: ArmController) -> None:
        """Execute a saved motion sequence on the arm."""
        motion = self.pose_store.load_motion(name)
        for step in motion.steps:
            if step.pose is not None:
                joints = self.pose_store.load_pose(step.pose)
            else:
                joints = step.joints  # type: ignore[assignment]
            arm.move_joints(joints)
            time.sleep(step.duration_s)
            if step.hold_s > 0:
                time.sleep(step.hold_s)
