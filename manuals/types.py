from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


ComponentRole = Literal[
    "ACTIVE_BLOCK",
    "DIMMED_OLD_BLOCK",
    "ARROW",
    "TEXT",
    "BACKGROUND",
    "UNKNOWN",
]

ReaderMode = Literal["new-pieces", "visible-blocks"]


@dataclass(frozen=True)
class BlockRequirement:
    color: str
    quantity: int | None
    confidence: float | None


@dataclass(frozen=True)
class DetectedColorRegion:
    color: str
    bbox: tuple[int, int, int, int]
    confidence: float | None
    area: int | None = None
    rejection_reason: str | None = None
    role: ComponentRole = "ACTIVE_BLOCK"
    component_id: int | None = None
    metrics: dict[str, float | int | str | bool] = field(default_factory=dict)


@dataclass(frozen=True)
class ManualStageResult:
    stage_id: str
    blocks: list[BlockRequirement] = field(default_factory=list)
    source_images: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    detected_regions: list[DetectedColorRegion] = field(default_factory=list)
    page_filename: str | None = None
    mode: ReaderMode = "new-pieces"
    status: str = "ok"
    accepted_components: list[DetectedColorRegion] = field(default_factory=list)
    rejected_components: list[DetectedColorRegion] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
