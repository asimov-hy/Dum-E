from __future__ import annotations

from manuals.types import ManualStageResult


def format_manual_stage_result(result: ManualStageResult) -> str:
    lines = [
        f"Stage: {result.stage_id}",
        f"Mode: {result.mode}",
        f"Status: {result.status}",
        "Required active colors:",
    ]

    if result.active_colors:
        lines.extend(f"- {color}" for color in result.active_colors)
    else:
        lines.append("- none detected")

    if result.blocks:
        lines.append("")
        lines.append("Component counts:")
        for block in result.blocks:
            quantity = "unknown" if block.quantity is None else str(block.quantity)
            lines.append(f"- {block.color}: {quantity}")

    if result.notes:
        lines.append("")
        lines.append("Notes:")
        lines.extend(f"- {note}" for note in result.notes)

    return "\n".join(lines)
