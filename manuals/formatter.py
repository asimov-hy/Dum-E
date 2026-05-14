from __future__ import annotations

from manuals.types import ManualStageResult


def format_manual_stage_result(result: ManualStageResult) -> str:
    lines = [
        f"Stage: {result.stage_id}",
        f"Mode: {result.mode}",
        f"Status: {result.status}",
        "Required colored blocks:",
    ]

    if result.blocks:
        for block in result.blocks:
            quantity = "unknown" if block.quantity is None else str(block.quantity)
            lines.append(f"- {block.color}: {quantity}")
    else:
        lines.append("- none detected")

    if result.notes:
        lines.append("")
        lines.append("Notes:")
        lines.extend(f"- {note}" for note in result.notes)

    return "\n".join(lines)
