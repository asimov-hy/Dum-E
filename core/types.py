"""Core protocol contracts for MediaPipeline sources."""

from typing import Protocol

from core.frame import Frame


class FrameSource(Protocol):
    """Source capable of yielding validated RGB ``Frame`` objects."""

    def start(self) -> None: ...

    def stop(self) -> None: ...

    def get_frame(self) -> Frame: ...
