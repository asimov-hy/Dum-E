from __future__ import annotations

import logging
import os
import tempfile
import time
from collections.abc import Callable, Sequence
from typing import Protocol

from perception.types import GestureEvent, GestureServiceConfig, GestureType

LoopAction = str

_LOGGER = logging.getLogger(__name__)

GESTURE_ACTIONS: dict[GestureType, LoopAction] = {
    GestureType.THUMBS_UP: "advance",
    GestureType.TWO_FINGERS: "repeat",
    GestureType.FIST: "quit",
}


class FrameSourceLike(Protocol):
    def start(self) -> None: ...

    def stop(self) -> None: ...

    def get_frame(self) -> object: ...


class GestureServiceLike(Protocol):
    def process_frame(self, frame: object) -> Sequence[GestureEvent]: ...

    def close(self) -> None: ...


WaitFunc = Callable[[str], LoopAction]


def loop_action_from_gesture_event(event: GestureEvent) -> LoopAction | None:
    return GESTURE_ACTIONS.get(event.type)


def loop_action_from_gesture_events(events: Sequence[GestureEvent]) -> LoopAction | None:
    for event in events:
        action = loop_action_from_gesture_event(event)
        if action is not None:
            return action
    return None


class GestureManualWait:
    """Blocking gesture-backed wait function for the manual page loop."""

    def __init__(
        self,
        *,
        source: FrameSourceLike,
        gesture_service: GestureServiceLike,
        timeout_s: float | None = None,
        fallback_wait_func: WaitFunc | None = None,
        poll_delay_s: float = 0.01,
        log_interval_s: float = 1.0,
        clock: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        if timeout_s is not None and timeout_s < 0:
            raise ValueError("timeout_s must not be negative")
        if poll_delay_s < 0:
            raise ValueError("poll_delay_s must not be negative")
        if log_interval_s < 0:
            raise ValueError("log_interval_s must not be negative")

        self.source = source
        self.gesture_service = gesture_service
        self.timeout_s = timeout_s
        self.fallback_wait_func = fallback_wait_func
        self.poll_delay_s = poll_delay_s
        self.log_interval_s = log_interval_s
        self.clock = clock
        self.sleeper = sleeper
        self._started = False
        self._service_closed = False
        self._last_log_at = -float("inf")

    def start(self) -> None:
        if self._started:
            return
        try:
            self.source.start()
        except Exception:
            try:
                self.close()
            except Exception:
                _LOGGER.exception("Gesture wait cleanup failed after source startup error.")
            raise
        self._started = True

    def close(self) -> None:
        close_error: Exception | None = None
        service_close = getattr(self.gesture_service, "close", None)
        if service_close is not None and not self._service_closed:
            try:
                service_close()
                self._service_closed = True
            except Exception as exc:
                close_error = exc
        if self._started:
            try:
                self.source.stop()
                self._started = False
            except Exception as exc:
                if close_error is None:
                    close_error = exc
        if close_error is not None:
            raise close_error

    def __enter__(self) -> "GestureManualWait":
        self.start()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def __call__(self, wait_mode: str = "gesture") -> LoopAction:
        if wait_mode != "gesture":
            raise ValueError(f"Unsupported wait mode for gesture wait: {wait_mode}")

        self.start()
        deadline = None if self.timeout_s is None else self.clock() + self.timeout_s

        while True:
            if deadline is not None and self.clock() >= deadline:
                return self._timeout_action()

            try:
                frame = self.source.get_frame()
            except EOFError:
                _LOGGER.warning("Gesture frame source ended before a command gesture was detected.")
                return self._timeout_action()

            events = list(self.gesture_service.process_frame(frame))
            action = loop_action_from_gesture_events(events)
            if action is not None:
                self._log_events(events, action=action)
                return action

            self._log_events(events, action=None)
            if self.poll_delay_s:
                self.sleeper(self.poll_delay_s)

    def _timeout_action(self) -> LoopAction:
        if self.fallback_wait_func is not None:
            print("Gesture wait timed out; falling back to keyboard input.")
            return self.fallback_wait_func("enter")
        print("Gesture wait timed out; quitting manual loop for safety.")
        return "quit"

    def _log_events(self, events: Sequence[GestureEvent], *, action: LoopAction | None) -> None:
        if self.log_interval_s == 0:
            return

        now = self.clock()
        if now - self._last_log_at < self.log_interval_s:
            return
        self._last_log_at = now

        if not events:
            _LOGGER.debug("gesture_wait events=none action=none")
            return

        latest = events[-1]
        _LOGGER.debug(
            "gesture_wait latest=%s confidence=%.3f source=%s action=%s",
            latest.type.name,
            latest.confidence,
            latest.source.name,
            action or "none",
        )


def build_gesture_wait(
    *,
    source_name: str = "webcam",
    video_path: str | None = None,
    model_path: str = "data/mediapipe/models/gesture_recognizer.task",
    timeout_s: float | None = None,
    fallback_wait_func: WaitFunc | None = None,
) -> GestureManualWait:
    mpl_config_dir = os.path.join(tempfile.gettempdir(), "dume_mplconfig")
    os.makedirs(mpl_config_dir, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", mpl_config_dir)

    from camera.source import create_source
    from perception.gesture import GestureService

    source_kwargs: dict[str, object] = {}
    normalized_source = source_name.lower()
    if normalized_source == "video":
        if video_path is None:
            raise ValueError("--gesture-video-path is required when --gesture-source video")
        source_kwargs["path"] = video_path

    source = create_source(normalized_source, **source_kwargs)
    gesture_service = GestureService(GestureServiceConfig(model_path=model_path))
    return GestureManualWait(
        source=source,
        gesture_service=gesture_service,
        timeout_s=timeout_s,
        fallback_wait_func=fallback_wait_func,
    )
