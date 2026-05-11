from __future__ import annotations

import subprocess
import sys
from argparse import Namespace
from pathlib import Path

import scripts.mediapipe.record_regression_clip as recorder


def test_recording_script_imports_without_camera_hardware() -> None:
    assert recorder.parse_args is not None


def test_recording_script_help_runs_without_camera_hardware() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/mediapipe/record_regression_clip.py", "--help"],
        check=False,
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "--source" in result.stdout
    assert "--clip-id" in result.stdout


def test_recording_argparse_accepts_required_scaffold_fields() -> None:
    args = recorder.parse_args(
        [
            "--source",
            "webcam",
            "--output",
            "data/mediapipe/regression_media/webcam/thumbs_up.mp4",
            "--clip-id",
            "webcam_thumbs_up",
            "--expected",
            "THUMBS_UP",
            "--suite",
            "webcam",
            "--camera-backend",
            "webcam",
            "--camera-model",
            "Laptop Webcam",
            "--resolution",
            "640x480",
            "--fps",
            "30",
            "--duration-seconds",
            "3",
            "--notes",
            "unit test parse only",
        ]
    )

    assert args.source == "webcam"
    assert args.clip_id == "webcam_thumbs_up"
    assert args.expected == "THUMBS_UP"
    assert args.suite == "webcam"
    assert args.camera_backend == "webcam"


def test_recording_metadata_and_manifest_suggestion_are_hardware_free() -> None:
    args = Namespace(
        clip_id="clip",
        expected="NONE",
        suite="custom",
        source="webcam",
        camera_backend="webcam",
        camera_model="model",
        resolution="640x480",
        fps=30.0,
        duration_seconds=3.0,
        notes="notes",
    )

    metadata = recorder._metadata(args, frame_count=90)
    manifest_entry = recorder._suggest_manifest_entry(
        args,
        Path("data/mediapipe/regression_media/custom/clip.mp4"),
    )

    assert metadata["frame_count"] == 90
    assert manifest_entry["present"] is True
    assert manifest_entry["expected_type"] == "NONE"
    assert manifest_entry["kind"] == "none"
