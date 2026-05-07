"""OpenCV video-file source for recorded regression media."""

from __future__ import annotations

import importlib
from pathlib import Path
from types import ModuleType
from typing import Any

import numpy as np

from core.frame import Frame, validate_frame


class VideoFileFrameSource:
    """FrameSource implementation backed by ``cv2.VideoCapture`` on a file.

    Timestamps are deterministic for regression: ``round(frame_id * 1000 / fps)``.
    """

    def __init__(
        self,
        path: str | Path,
        *,
        camera_name: str | None = None,
        fps: float | None = None,
    ) -> None:
        self.path = Path(path)
        self.camera_name = camera_name or f"video:{self.path}"
        self.requested_fps = fps
        self.fps: float | None = None
        self._capture: Any | None = None
        self._cv2: ModuleType | None = None
        self._next_frame_id = 0

    def start(self) -> None:
        if self._capture is not None:
            return
        if not self.path.is_file():
            raise FileNotFoundError(f"Video file not found: {self.path}")

        try:
            cv2 = importlib.import_module("cv2")
        except ImportError as exc:
            raise RuntimeError(
                "VideoFileFrameSource requires OpenCV. Install opencv-python "
                "or use backend='fake' for hardware-free unit tests."
            ) from exc

        capture = cv2.VideoCapture(str(self.path))
        if not capture.isOpened():
            capture.release()
            raise RuntimeError(f"Could not open video file: {self.path}")

        detected_fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
        self.fps = self.requested_fps or (detected_fps if detected_fps > 0 else 30.0)
        self._capture = capture
        self._cv2 = cv2
        self._next_frame_id = 0

    def stop(self) -> None:
        if self._capture is None:
            return
        self._capture.release()
        self._capture = None

    def get_frame(self) -> Frame:
        if self._capture is None or self._cv2 is None or self.fps is None:
            raise RuntimeError("VideoFileFrameSource.start() must be called before get_frame()")

        ok, bgr = self._capture.read()
        if not ok or bgr is None:
            raise EOFError(f"End of video file reached: {self.path}")

        rgb = self._cv2.cvtColor(bgr, self._cv2.COLOR_BGR2RGB)
        rgb = np.ascontiguousarray(rgb, dtype=np.uint8)
        frame_id = self._next_frame_id
        frame = Frame(
            rgb=rgb,
            timestamp_ms=round(frame_id * 1000 / self.fps),
            frame_id=frame_id,
            camera_name=self.camera_name,
        )
        validate_frame(frame)
        self._next_frame_id += 1
        return frame

    def __enter__(self) -> "VideoFileFrameSource":
        self.start()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.stop()
