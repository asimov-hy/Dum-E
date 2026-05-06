"""Camera source factory and hardware-free fake source."""

from collections.abc import Sequence

import numpy as np

from camera.lerobot_adapter import create_lerobot_source
from camera.opencv_backend import OpenCVFrameSource
from camera.realsense_backend import RealSenseFrameSource
from core.frame import Frame, validate_frame
from core.types import FrameSource


class FakeSource(FrameSource):
    """Deterministic RGB frame source for tests and camera-pipeline dry runs."""

    def __init__(
        self,
        frames: Sequence[Frame] | None = None,
        *,
        width: int = 640,
        height: int = 480,
        camera_name: str = "fake",
        start_timestamp_ms: int = 0,
        timestamp_step_ms: int = 33,
    ) -> None:
        if width <= 0:
            raise ValueError("width must be positive")
        if height <= 0:
            raise ValueError("height must be positive")
        if timestamp_step_ms <= 0:
            raise ValueError("timestamp_step_ms must be positive")

        self._frames = tuple(frames) if frames is not None else None
        if self._frames is not None and not self._frames:
            raise ValueError("frames must be non-empty when provided")

        self.width = width
        self.height = height
        self.camera_name = camera_name
        self.start_timestamp_ms = start_timestamp_ms
        self.timestamp_step_ms = timestamp_step_ms
        self.start_count = 0
        self.stop_count = 0
        self._running = False
        self._next_frame_id = 0
        self._last_timestamp_ms = start_timestamp_ms

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self) -> None:
        if self._running:
            return

        self._running = True
        self.start_count += 1
        self._next_frame_id = 0
        self._last_timestamp_ms = self.start_timestamp_ms

    def stop(self) -> None:
        if not self._running:
            return

        self._running = False
        self.stop_count += 1

    def get_frame(self) -> Frame:
        if not self._running:
            raise RuntimeError("FakeSource.start() must be called before get_frame()")

        frame_id = self._next_frame_id
        timestamp_ms = self._last_timestamp_ms + self.timestamp_step_ms
        rgb, depth_m = self._next_payload(frame_id)

        frame = Frame(
            rgb=rgb,
            timestamp_ms=timestamp_ms,
            frame_id=frame_id,
            depth_m=depth_m,
            camera_name=self.camera_name,
        )
        validate_frame(frame)

        self._next_frame_id += 1
        self._last_timestamp_ms = timestamp_ms
        return frame

    def __enter__(self) -> "FakeSource":
        self.start()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.stop()

    def _next_payload(self, frame_id: int) -> tuple[np.ndarray, np.ndarray | None]:
        if self._frames is not None:
            frame = self._frames[frame_id % len(self._frames)]
            depth_m = None
            if frame.depth_m is not None:
                depth_m = np.ascontiguousarray(frame.depth_m)
            return np.ascontiguousarray(frame.rgb, dtype=np.uint8), depth_m

        x = np.arange(self.width, dtype=np.uint16)[None, :]
        y = np.arange(self.height, dtype=np.uint16)[:, None]
        rgb = np.empty((self.height, self.width, 3), dtype=np.uint8)
        rgb[:, :, 0] = (x + frame_id) % 256
        rgb[:, :, 1] = (y + frame_id * 3) % 256
        rgb[:, :, 2] = (frame_id * 17) % 256
        return np.ascontiguousarray(rgb), None


def create_source(backend: str = "fake", **kwargs: object) -> FrameSource:
    """Create a camera source by backend name."""

    normalized = backend.lower()
    if normalized == "fake":
        return FakeSource(**kwargs)
    if normalized in {"webcam", "opencv"}:
        if "device" in kwargs:
            kwargs = {**kwargs, "device": _coerce_device(kwargs["device"])}
        return OpenCVFrameSource(**kwargs)
    if normalized == "realsense":
        return RealSenseFrameSource(**kwargs)
    if normalized == "lerobot":
        return create_lerobot_source(**kwargs)

    raise ValueError(
        f"Unknown camera backend '{backend}'. "
        "Supported backends: fake, webcam, opencv, realsense, lerobot."
    )


def _coerce_device(device: object) -> object:
    if isinstance(device, str) and device.lstrip("-").isdigit():
        return int(device)
    return device
