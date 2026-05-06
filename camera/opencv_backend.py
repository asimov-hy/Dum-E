"""OpenCV webcam source.

OpenCV is imported lazily in ``start()`` so hardware-free tests do not require
the ``cv2`` package.
"""

from __future__ import annotations

import importlib
import logging
import time
from types import ModuleType
from typing import Any

import numpy as np

from core.frame import Frame, validate_frame


_LOGGER = logging.getLogger(__name__)


class OpenCVFrameSource:
    """FrameSource implementation backed by ``cv2.VideoCapture``."""

    def __init__(
        self,
        *,
        device: int | str = 0,
        width: int | None = None,
        height: int | None = None,
        camera_name: str | None = None,
    ) -> None:
        self.device = device
        self.width = width
        self.height = height
        self.camera_name = camera_name or f"webcam:{device}"
        self.actual_width: int | None = None
        self.actual_height: int | None = None
        self._capture: Any | None = None
        self._cv2: ModuleType | None = None
        self._next_frame_id = 0
        self._last_timestamp_ms = -1

    def start(self) -> None:
        if self._capture is not None:
            return

        try:
            cv2 = importlib.import_module("cv2")
        except ImportError as exc:
            raise RuntimeError(
                "OpenCVFrameSource requires OpenCV. Install opencv-python or "
                "use backend='fake' for hardware-free tests."
            ) from exc

        capture = cv2.VideoCapture(self.device)
        if self.width is not None:
            capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        if self.height is not None:
            capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

        if not capture.isOpened():
            capture.release()
            raise RuntimeError(f"Could not open OpenCV camera device {self.device!r}")

        self.actual_width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.actual_height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self._warn_on_resolution_mismatch()

        self._capture = capture
        self._cv2 = cv2
        self._next_frame_id = 0
        self._last_timestamp_ms = -1

    def stop(self) -> None:
        if self._capture is None:
            return

        self._capture.release()
        self._capture = None

    def get_frame(self) -> Frame:
        if self._capture is None or self._cv2 is None:
            raise RuntimeError("OpenCVFrameSource.start() must be called before get_frame()")

        ok, bgr = self._capture.read()
        if not ok or bgr is None:
            raise RuntimeError(f"Could not read a frame from OpenCV camera {self.device!r}")

        rgb = self._cv2.cvtColor(bgr, self._cv2.COLOR_BGR2RGB)
        rgb = np.ascontiguousarray(rgb, dtype=np.uint8)
        timestamp_ms = self._next_timestamp_ms()
        frame = Frame(
            rgb=rgb,
            timestamp_ms=timestamp_ms,
            frame_id=self._next_frame_id,
            camera_name=self.camera_name,
        )
        validate_frame(frame)

        self._next_frame_id += 1
        return frame

    def __enter__(self) -> "OpenCVFrameSource":
        self.start()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.stop()

    def _next_timestamp_ms(self) -> int:
        timestamp_ms = time.monotonic_ns() // 1_000_000
        if timestamp_ms <= self._last_timestamp_ms:
            timestamp_ms = self._last_timestamp_ms + 1
        self._last_timestamp_ms = timestamp_ms
        return timestamp_ms

    def _warn_on_resolution_mismatch(self) -> None:
        requested = (self.width, self.height)
        actual = (self.actual_width, self.actual_height)
        if self.width is not None and self.actual_width != self.width:
            _LOGGER.warning("Requested webcam width %s, got %s", self.width, self.actual_width)
        if self.height is not None and self.actual_height != self.height:
            _LOGGER.warning("Requested webcam height %s, got %s", self.height, self.actual_height)
        if requested != (None, None):
            _LOGGER.info("Webcam resolution requested=%s actual=%s", requested, actual)
