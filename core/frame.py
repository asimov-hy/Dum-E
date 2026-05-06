"""Frame contract shared by camera and perception packages."""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Frame:
    """A single RGB camera frame.

    ``rgb`` is RGB, ``uint8``, HWC, and C-contiguous.
    ``timestamp_ms`` is monotonic and strictly increasing for live streams.
    """

    rgb: np.ndarray
    timestamp_ms: int
    frame_id: int | None = None
    depth_m: np.ndarray | None = None
    camera_name: str | None = None


def validate_frame(frame: Frame) -> None:
    """Validate the Phase 0 frame data contract."""

    assert frame.rgb.ndim == 3, f"Expected 3D array, got {frame.rgb.ndim}D"
    assert frame.rgb.shape[2] == 3, f"Expected 3 channels, got {frame.rgb.shape[2]}"
    assert frame.rgb.dtype == np.uint8, f"Expected uint8, got {frame.rgb.dtype}"
    assert frame.rgb.flags["C_CONTIGUOUS"], "Array must be C-contiguous"
