"""MediaPipe Gesture Recognizer service with Phase 4 filtering."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.frame import Frame, validate_frame
from core.landmarks import Landmark2D, Landmark3D
from perception.filters import FilterChain
from perception.finger_state import FingerStateDetector
from perception.mapper import GestureMapper
from perception.types import GestureEvent, GestureObservation, GestureServiceConfig


@dataclass(frozen=True)
class _MediaPipeRuntime:
    recognizer: Any
    image_cls: Any
    image_format: Any


class GestureService:
    """Analyze RGB frames and emit command-relevant gesture events."""

    def __init__(self, config: GestureServiceConfig) -> None:
        self.config = config
        self._validate_model_path(config.model_path)
        self._runtime = _create_mediapipe_runtime(config)
        self._finger_detector = FingerStateDetector()
        self._mapper = GestureMapper(config.gesture_config)
        self._filters = FilterChain(config.filter_config)
        self._last_timestamp_ms = -1

    @property
    def last_filter_debug(self) -> dict[str, object]:
        return dict(self._filters.last_debug)

    def analyze_frame(self, frame: Frame) -> list[GestureObservation]:
        """Run MediaPipe inference and return all observations, including NONE."""

        validate_frame(frame)
        self._enforce_timestamp(frame.timestamp_ms)
        mp_image = self._runtime.image_cls(
            image_format=self._runtime.image_format,
            data=frame.rgb,
        )
        result = self._runtime.recognizer.recognize_for_video(
            mp_image,
            frame.timestamp_ms,
        )
        return self._build_observations(result, frame)

    def events_from_observations(
        self,
        frame: Frame,
        observations: Sequence[GestureObservation],
    ) -> list[GestureEvent]:
        """Filter existing observations into command events without inference."""

        return self._filters.apply(observations, frame=frame)

    def process_frame(self, frame: Frame) -> list[GestureEvent]:
        """Convenience wrapper: analyze once, then convert observations to events."""

        observations = self.analyze_frame(frame)
        return self.events_from_observations(frame, observations)

    def close(self) -> None:
        close = getattr(self._runtime.recognizer, "close", None)
        if close is not None:
            close()

    def _enforce_timestamp(self, timestamp_ms: int) -> None:
        if timestamp_ms <= self._last_timestamp_ms:
            raise ValueError(
                "timestamp_ms must be strictly increasing: "
                f"got {timestamp_ms}, previous {self._last_timestamp_ms}"
            )
        self._last_timestamp_ms = timestamp_ms

    def _build_observations(
        self,
        result: Any,
        frame: Frame,
    ) -> list[GestureObservation]:
        observations: list[GestureObservation] = []
        hand_landmarks = getattr(result, "hand_landmarks", None) or []
        gestures = getattr(result, "gestures", None) or []
        handednesses = getattr(result, "handedness", None) or []
        hand_world_landmarks = getattr(result, "hand_world_landmarks", None) or []

        for hand_index, landmarks in enumerate(hand_landmarks):
            raw_label = None
            raw_label_confidence = 0.0
            if hand_index < len(gestures) and gestures[hand_index]:
                top = gestures[hand_index][0]
                raw_label = getattr(top, "category_name", None)
                raw_label_confidence = float(getattr(top, "score", 0.0))

            handedness = None
            if hand_index < len(handednesses) and handednesses[hand_index]:
                handedness = getattr(handednesses[hand_index][0], "category_name", None)

            landmarks_2d = tuple(
                Landmark2D(
                    x=float(landmark.x),
                    y=float(landmark.y),
                    z=float(landmark.z),
                )
                for landmark in landmarks
            )

            world_landmarks = None
            if hand_index < len(hand_world_landmarks) and hand_world_landmarks[hand_index]:
                world_landmarks = tuple(
                    Landmark3D(
                        x=float(landmark.x),
                        y=float(landmark.y),
                        z=float(landmark.z),
                    )
                    for landmark in hand_world_landmarks[hand_index]
                )

            finger_state_result = self._finger_detector.detect(
                landmarks_2d,
                world_landmarks,
                handedness,
            )
            finger_state = finger_state_result.state
            finger_count = sum(
                [
                    finger_state.thumb,
                    finger_state.index,
                    finger_state.middle,
                    finger_state.ring,
                    finger_state.pinky,
                ]
            )
            mapped = self._mapper.map(
                raw_label=raw_label,
                raw_confidence=raw_label_confidence,
                finger_state_result=finger_state_result,
            )

            observations.append(
                GestureObservation(
                    type=mapped.type,
                    confidence=mapped.confidence,
                    source=mapped.source,
                    timestamp_ms=frame.timestamp_ms,
                    handedness=handedness,
                    hand_index=hand_index,
                    landmarks=landmarks_2d,
                    world_landmarks=world_landmarks,
                    finger_count=finger_count,
                    finger_state=finger_state,
                    finger_state_result=finger_state_result,
                    raw_label=raw_label,
                    raw_label_confidence=raw_label_confidence,
                    camera_name=frame.camera_name,
                    frame_id=frame.frame_id,
                )
            )

        return observations

    @staticmethod
    def _validate_model_path(model_path: str) -> None:
        path = Path(model_path)
        if not path.is_file():
            raise FileNotFoundError(
                f"MediaPipe gesture model not found at '{model_path}'. "
                "Run `python scripts/mediapipe/download_gesture_model.py` or pass "
                "GestureServiceConfig(model_path=...) with a local .task file."
            )


def _create_mediapipe_runtime(config: GestureServiceConfig) -> _MediaPipeRuntime:
    try:
        import mediapipe as mp
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision
    except ImportError as exc:
        raise RuntimeError(
            "GestureService requires MediaPipe for live inference. Install the "
            "mediapipe package after downloading the gesture_recognizer.task model."
        ) from exc

    base_options = mp_python.BaseOptions(model_asset_path=config.model_path)
    options = vision.GestureRecognizerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.VIDEO,
        num_hands=config.max_num_hands,
        min_hand_detection_confidence=config.min_hand_detection_confidence,
        min_hand_presence_confidence=config.min_hand_presence_confidence,
        min_tracking_confidence=config.min_tracking_confidence,
    )
    recognizer = vision.GestureRecognizer.create_from_options(options)
    return _MediaPipeRuntime(
        recognizer=recognizer,
        image_cls=mp.Image,
        image_format=mp.ImageFormat.SRGB,
    )
