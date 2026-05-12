"""Manual-reading subsystem for extracting human-readable build requirements."""

from manuals.reader import ImageLoadError, read_manual
from manuals.types import BlockRequirement, DetectedColorRegion, ManualStageResult

__all__ = [
    "BlockRequirement",
    "DetectedColorRegion",
    "ImageLoadError",
    "ManualStageResult",
    "read_manual",
]
