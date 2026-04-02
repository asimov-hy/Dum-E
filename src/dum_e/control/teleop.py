from __future__ import annotations


class TeleopService:
    """Human-readable teleop plan until a live controller is wired in."""

    def describe(self) -> str:
        return (
            "Teleop is not connected to live hardware yet.\n"
            "Planned operator defaults:\n"
            "- low-speed joint jogging\n"
            "- explicit enable/disable flow\n"
            "- named-pose shortcuts\n"
            "- emergency stop binding\n"
            "- optional gamepad support after keyboard jog is stable"
        )
