"""Low-speed joint jogging with explicit enable/disable gating."""

from __future__ import annotations

import sys
import time

from dum_e.control.arm import ArmController

DEFAULT_STEP_DEG = 1.0
MIN_STEP_DEG = 0.1
MAX_STEP_DEG = 5.0
JOG_RATE_HZ = 10


class TeleopService:
    """Keyboard-driven joint jogging with enable/disable safety gate."""

    def __init__(self, arm: ArmController) -> None:
        self.arm = arm
        self._active_joint: int = 0
        self._step_deg: float = DEFAULT_STEP_DEG

    @property
    def is_enabled(self) -> bool:
        return self.arm.is_enabled

    def enable(self) -> None:
        self.arm.enable()

    def disable(self) -> None:
        self.arm.disable()

    def select_joint(self, index: int) -> str:
        """Select the active joint by index. Returns the joint name."""
        if not 0 <= index < len(self.arm.motors):
            raise ValueError(f"Joint index {index} out of range (0-{len(self.arm.motors) - 1})")
        self._active_joint = index
        return self.arm.motors[index].name

    def jog_positive(self) -> float:
        """Jog the active joint in the positive direction. Returns new position."""
        return self.arm.jog_joint(self._active_joint, self._step_deg)

    def jog_negative(self) -> float:
        """Jog the active joint in the negative direction. Returns new position."""
        return self.arm.jog_joint(self._active_joint, -self._step_deg)

    def set_step_size(self, deg: float) -> float:
        """Set jog step size, clamped to safe range. Returns actual step size."""
        self._step_deg = max(MIN_STEP_DEG, min(MAX_STEP_DEG, deg))
        return self._step_deg

    def describe(self) -> str:
        joint_name = self.arm.motors[self._active_joint].name
        state = "ENABLED" if self.is_enabled else "DISABLED"
        lines = [
            f"Teleop state: {state}",
            f"Active joint: [{self._active_joint}] {joint_name}",
            f"Step size: {self._step_deg} deg",
            "",
            "Controls:",
            "  e       — enable torque (required before jogging)",
            "  d       — disable torque",
            "  0-5     — select joint by index",
            "  +/=     — jog active joint positive",
            "  -       — jog active joint negative",
            "  [       — decrease step size",
            "  ]       — increase step size",
            "  p       — print current joint positions",
            "  q       — quit teleop",
        ]
        return "\n".join(lines)

    def run_interactive(self) -> None:
        """Blocking interactive teleop loop. Reads single keypresses."""
        print(self.describe())
        print()

        try:
            while True:
                key = _read_key()
                if key is None:
                    time.sleep(1.0 / JOG_RATE_HZ)
                    continue

                if key == "q":
                    break
                elif key == "e":
                    self.enable()
                    print("Torque ENABLED")
                elif key == "d":
                    self.disable()
                    print("Torque DISABLED")
                elif key in "0123456789" and int(key) < len(self.arm.motors):
                    name = self.select_joint(int(key))
                    print(f"Selected joint [{key}] {name}")
                elif key in ("+", "="):
                    try:
                        pos = self.jog_positive()
                        name = self.arm.motors[self._active_joint].name
                        print(f"  {name} -> {pos} deg")
                    except RuntimeError as exc:
                        print(f"  {exc}")
                elif key == "-":
                    try:
                        pos = self.jog_negative()
                        name = self.arm.motors[self._active_joint].name
                        print(f"  {name} -> {pos} deg")
                    except RuntimeError as exc:
                        print(f"  {exc}")
                elif key == "[":
                    actual = self.set_step_size(self._step_deg / 2)
                    print(f"Step size: {actual} deg")
                elif key == "]":
                    actual = self.set_step_size(self._step_deg * 2)
                    print(f"Step size: {actual} deg")
                elif key == "p":
                    joints = self.arm.read_joints()
                    for i, (motor, val) in enumerate(zip(self.arm.motors, joints)):
                        marker = " *" if i == self._active_joint else ""
                        print(f"  [{i}] {motor.name}: {val} deg{marker}")
        finally:
            if self.is_enabled:
                self.disable()
                print("Torque disabled on exit.")


def _read_key() -> str | None:
    """Read a single keypress without blocking. Returns None if no key available."""
    if sys.platform == "win32":
        import msvcrt

        if msvcrt.kbhit():
            ch = msvcrt.getch()
            return ch.decode("utf-8", errors="ignore")
        return None
    else:
        import select
        import termios
        import tty

        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ready, _, _ = select.select([sys.stdin], [], [], 0.0)
            if ready:
                return sys.stdin.read(1)
            return None
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
