from __future__ import annotations

import json
import os
import statistics
import time
from collections import Counter
from pathlib import Path
from typing import Any

import pytest

from camera.video_backend import VideoFileFrameSource
from perception.gesture import GestureService
from perception.types import GestureServiceConfig, GestureType


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "data" / "mediapipe" / "regression_media" / "manifest.json"
DEFAULT_MODEL_PATH = (
    REPO_ROOT / "data" / "mediapipe" / "models" / "gesture_recognizer.task"
)
TARGET_TYPES = {
    "THUMBS_UP",
    "FIST",
    "PALM",
    "ONE_FINGER",
    "TWO_FINGERS",
    "THREE_FINGERS",
}
REQUIRED_CLIP_IDS = {
    "thumbs_up_clear",
    "fist_clear",
    "palm_clear",
    "index_only",
    "index_middle",
    "index_middle_ring",
    "middle_only",
    "ring_only",
    "thumb_index",
    "four_fingers_thumb_folded",
    "no_hand",
    "partial_hand_entering",
    "partial_hand_leaving",
    "poor_lighting",
    "motion_blur",
    "two_hands_visible",
    "thumbs_up_side_angle",
    "three_finger_ring_stress",
    "raw_label_oscillation",
}


def _load_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_manifest_declares_required_phase5_coverage() -> None:
    manifest = _load_manifest()
    clips = manifest["clips"]
    ids = {clip["id"] for clip in clips}

    assert REQUIRED_CLIP_IDS <= ids
    for clip in clips:
        assert clip.get("expected_type", clip.get("expected")) in TARGET_TYPES | {"NONE"}
        assert clip["kind"] in {"target", "none"}
        assert isinstance(clip["path"], str)
        assert isinstance(clip.get("present", False), bool)


@pytest.mark.parametrize("clip", _load_manifest()["clips"], ids=lambda clip: clip["id"])
def test_recorded_media_clip_regression(clip: dict[str, Any]) -> None:
    media_path = _clip_path(clip)
    if not clip.get("present", False):
        if _strict_media_required() and clip.get("required_for_phase5", False):
            pytest.fail(
                f"{clip['id']} is required_for_phase5 but not present. "
                "Phase 5 cannot PASS until required clips are recorded."
            )
        pytest.skip(
            f"{clip['id']} is declared but not present. Phase 5 is not PASS until "
            "recorded media is supplied and this test runs."
        )
    if not media_path.is_file():
        if _strict_media_required() and clip.get("required_for_phase5", False):
            pytest.fail(
                f"{clip['id']} is required_for_phase5 but missing at {media_path}."
            )
        pytest.skip(
            f"{clip['id']} is marked present but file is missing at {media_path}. "
            "Phase 5 is not PASS until the clip exists."
        )

    model_path = Path(os.environ.get("DUME_GESTURE_MODEL", DEFAULT_MODEL_PATH))
    if not model_path.is_file():
        pytest.skip(
            f"Gesture model missing at {model_path}. Run scripts/mediapipe/download_gesture_model.py."
        )
    pytest.importorskip("mediapipe")

    summary = _run_clip(clip, media_path=media_path, model_path=model_path)
    print(json.dumps(summary, indent=2, sort_keys=True))
    _write_report_if_requested(summary)

    expected_type = GestureType[clip.get("expected_type", clip["expected"])]
    if expected_type is GestureType.NONE:
        assert summary["observed_events"] == []
    else:
        assert summary["expected_event_count"] >= 1
        assert summary["wrong_event_count"] <= summary["expected_event_count"]


def _run_clip(
    clip: dict[str, Any],
    *,
    media_path: Path,
    model_path: Path,
) -> dict[str, Any]:
    expected_type = GestureType[clip.get("expected_type", clip["expected"])]
    raw_labels: Counter[str] = Counter()
    sources: Counter[str] = Counter()
    observed_events: list[str] = []
    event_timestamps: list[int] = []
    latencies_ms: list[float] = []
    frame_count = 0

    source = VideoFileFrameSource(media_path, camera_name=f"regression:{clip['id']}")
    service = GestureService(GestureServiceConfig(model_path=str(model_path)))
    try:
        source.start()
        while True:
            try:
                frame = source.get_frame()
            except EOFError:
                break
            started = time.perf_counter()
            observations = service.analyze_frame(frame)
            events = service.events_from_observations(frame, observations)
            latencies_ms.append((time.perf_counter() - started) * 1000)
            frame_count += 1

            for obs in observations:
                raw_labels[str(obs.raw_label)] += 1
                sources[obs.source.name] += 1
            for event in events:
                observed_events.append(event.type.name)
                event_timestamps.append(event.timestamp_ms)
    finally:
        service.close()
        source.stop()

    if frame_count == 0:
        raise AssertionError(f"Regression clip {clip['id']} produced no frames")

    expected_count = observed_events.count(expected_type.name)
    wrong_count = sum(
        1
        for event_name in observed_events
        if expected_type is GestureType.NONE or event_name != expected_type.name
    )
    first_detection_timestamp = (
        event_timestamps[observed_events.index(expected_type.name)]
        if expected_type.name in observed_events
        else None
    )
    first_detection_frame = (
        round(first_detection_timestamp * (source.fps or 30.0) / 1000)
        if first_detection_timestamp is not None
        else None
    )

    return {
        "clip_id": clip["id"],
        "expected_type": expected_type.name,
        "kind": clip["kind"],
        "frame_count": frame_count,
        "observed_events": observed_events,
        "first_detection_timestamp_ms": first_detection_timestamp,
        "first_detection_frame": first_detection_frame,
        "time_to_event_ms": first_detection_timestamp,
        "expected_event_count": expected_count,
        "wrong_event_count": wrong_count,
        "miss": expected_type is not GestureType.NONE and expected_count == 0,
        "false_positive": expected_type is GestureType.NONE and bool(observed_events),
        "raw_label_distribution": dict(raw_labels),
        "source_distribution": dict(sources),
        "average_latency_ms": statistics.fmean(latencies_ms) if latencies_ms else None,
        "p95_latency_ms": _p95(latencies_ms),
        "six_target_accuracy_sample": (
            expected_count >= 1 and wrong_count <= expected_count
            if expected_type.name in TARGET_TYPES
            else None
        ),
        "none_rejection_pass": (
            not observed_events if expected_type is GestureType.NONE else None
        ),
    }


def _clip_path(clip: dict[str, Any]) -> Path:
    external_root = os.environ.get("DUME_TEST_MEDIA_DIR")
    root = Path(external_root) if external_root else MANIFEST_PATH.parent
    return root / clip["path"]


def _strict_media_required() -> bool:
    return os.environ.get("DUME_REQUIRE_REGRESSION_MEDIA") == "1"


def _p95(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, round((len(ordered) - 1) * 0.95))
    return ordered[index]


def _write_report_if_requested(summary: dict[str, Any]) -> None:
    report_path = os.environ.get("DUME_REGRESSION_REPORT")
    if not report_path:
        return
    path = Path(report_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing: list[dict[str, Any]] = []
    if path.is_file():
        existing = json.loads(path.read_text(encoding="utf-8"))
    existing.append(summary)
    path.write_text(json.dumps(existing, indent=2, sort_keys=True), encoding="utf-8")
