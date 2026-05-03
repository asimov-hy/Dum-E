from __future__ import annotations

from dume.control.arm import ArmDriver
from dume.control.recording import PoseStore
from dume.control.session import ControlSession


class ReplayService:
    """Builds readable replay plans before live execution is added."""

    def __init__(self, session: ControlSession, pose_store: PoseStore) -> None:
        self.session = session
        self.pose_store = pose_store

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

    def execute_pose(self, name: str, driver: ArmDriver) -> bool:
        """Execute a saved pose through an injected arm driver."""

        joints = self.pose_store.load_pose(name)
        return driver.move_joints(joints)

    def execute_motion(self, name: str, driver: ArmDriver) -> bool:
        """Execute a saved motion through an injected arm driver."""

        motion = self.pose_store.load_motion(name)
        for step in motion.steps:
            joints = self.pose_store.load_pose(step.pose) if step.pose is not None else step.joints
            if joints is None:
                raise ValueError("Motion step did not define a target")
            if not driver.move_joints(joints):
                return False
        return True
