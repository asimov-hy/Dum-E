from __future__ import annotations

import sys

import pytest

import scripts.check_regression_media as checker


MANIFEST_PATH = checker.DEFAULT_MANIFEST
TARGET_TYPES = {
    "THUMBS_UP",
    "FIST",
    "PALM",
    "ONE_FINGER",
    "TWO_FINGERS",
    "THREE_FINGERS",
}


REQUIRED_FIELDS = {
    "id",
    "path",
    "present",
    "expected",
    "expected_type",
    "category",
    "required_for_phase5",
    "required_for_acceptance",
    "suite",
    "camera_backend",
    "camera_model",
    "camera_serial",
    "resolution",
    "fps",
    "lighting",
    "background",
    "handedness",
    "distance_to_camera_m",
    "notes",
}


def test_manifest_entries_support_extended_phase5_schema() -> None:
    manifest = checker.load_manifest(MANIFEST_PATH)

    for clip in manifest["clips"]:
        assert REQUIRED_FIELDS <= set(clip)
        assert clip["expected"] == clip["expected_type"]
        assert clip["expected"] in TARGET_TYPES | {"NONE"}
        assert isinstance(clip["required_for_phase5"], bool)
        assert isinstance(clip["required_for_acceptance"], bool)


def test_manifest_declares_primary_webcam_and_realsense_suites() -> None:
    manifest = checker.load_manifest(MANIFEST_PATH)
    suites = {clip["suite"] for clip in manifest["clips"]}
    backends = {clip["camera_backend"] for clip in manifest["clips"]}

    assert {"primary", "webcam", "realsense_rgb"} <= suites
    assert {"webcam", "realsense"} <= backends


def test_media_checker_reports_missing_required_phase5_clips() -> None:
    summary = checker.summarize_manifest(
        checker.load_manifest(MANIFEST_PATH),
        manifest_path=MANIFEST_PATH,
    )

    assert summary["total_entries"] >= 19
    assert summary["required_for_phase5_missing"]
    assert "primary" in summary["by_suite"]


def test_media_checker_non_strict_exits_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        ["check_regression_media.py", "--manifest", str(MANIFEST_PATH)],
    )

    assert checker.main() == 0


def test_media_checker_strict_exits_nonzero_for_missing_required_clips(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        ["check_regression_media.py", "--manifest", str(MANIFEST_PATH), "--strict"],
    )

    assert checker.main() == 1


def test_media_checker_suite_filter_limits_report() -> None:
    manifest = checker.load_manifest(MANIFEST_PATH)
    summary = checker.summarize_manifest(
        manifest,
        manifest_path=MANIFEST_PATH,
        suite="realsense_rgb",
    )

    assert summary["by_suite"] == {"realsense_rgb": 1}
    assert summary["by_camera_backend"] == {"realsense": 1}
