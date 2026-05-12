from __future__ import annotations

from dataclasses import dataclass, field


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


@dataclass(frozen=True)
class ManualStageResult:
    stage_id: str
    blocks: list[BlockRequirement] = field(default_factory=list)
    source_images: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    detected_regions: list[DetectedColorRegion] = field(default_factory=list)
