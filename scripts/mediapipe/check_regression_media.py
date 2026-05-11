"""Check DUM-E regression media manifest status.

This script is intentionally hardware-free: it does not import MediaPipe,
OpenCV, RealSense, or any camera backend.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


DEFAULT_MANIFEST = Path("data/mediapipe/regression_media/manifest.json")


def main() -> int:
    args = _parse_args()
    manifest_path = Path(args.manifest)
    manifest = load_manifest(manifest_path)
    summary = summarize_manifest(
        manifest,
        manifest_path=manifest_path,
        suite=args.suite,
    )
    print_summary(summary)
    if args.strict and (summary["required_for_phase5_missing"] or summary["invalid_present"]):
        return 1
    return 0


def load_manifest(path: Path = DEFAULT_MANIFEST) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def summarize_manifest(
    manifest: dict[str, Any],
    *,
    manifest_path: Path = DEFAULT_MANIFEST,
    suite: str | None = None,
) -> dict[str, Any]:
    clips = [
        clip
        for clip in manifest.get("clips", [])
        if suite is None or clip.get("suite") == suite
    ]
    present: list[str] = []
    missing: list[str] = []
    invalid_present: list[str] = []
    required_for_phase5_missing: list[str] = []
    required_for_acceptance_missing: list[str] = []
    by_suite: Counter[str] = Counter()
    by_camera_backend: Counter[str] = Counter()
    missing_by_suite: dict[str, list[str]] = defaultdict(list)

    for clip in clips:
        clip_id = clip["id"]
        clip_suite = clip.get("suite", "unspecified")
        camera_backend = clip.get("camera_backend", "unspecified")
        by_suite[clip_suite] += 1
        by_camera_backend[camera_backend] += 1

        path = clip_path(clip, manifest_path=manifest_path)
        is_present = bool(clip.get("present", False))
        readable = _is_readable_file(path)
        if is_present and readable:
            present.append(clip_id)
            continue
        if is_present and not readable:
            invalid_present.append(clip_id)

        missing.append(clip_id)
        missing_by_suite[clip_suite].append(clip_id)
        if clip.get("required_for_phase5", False):
            required_for_phase5_missing.append(clip_id)
        if clip.get("required_for_acceptance", False):
            required_for_acceptance_missing.append(clip_id)

    return {
        "total_entries": len(clips),
        "present_clips": present,
        "missing_clips": missing,
        "invalid_present": invalid_present,
        "required_for_phase5_missing": required_for_phase5_missing,
        "required_for_acceptance_missing": required_for_acceptance_missing,
        "by_suite": dict(by_suite),
        "by_camera_backend": dict(by_camera_backend),
        "missing_by_suite": dict(missing_by_suite),
    }


def clip_path(clip: dict[str, Any], *, manifest_path: Path = DEFAULT_MANIFEST) -> Path:
    return manifest_path.parent / clip["path"]


def print_summary(summary: dict[str, Any]) -> None:
    print(f"total manifest entries: {summary['total_entries']}")
    print(f"present clips: {len(summary['present_clips'])}")
    print(f"missing clips: {len(summary['missing_clips'])}")
    print(
        "required_for_phase5 missing clips: "
        f"{len(summary['required_for_phase5_missing'])}"
    )
    print(
        "required_for_acceptance missing clips: "
        f"{len(summary['required_for_acceptance_missing'])}"
    )
    print(f"clips by suite: {json.dumps(summary['by_suite'], sort_keys=True)}")
    print(
        "clips by camera_backend: "
        f"{json.dumps(summary['by_camera_backend'], sort_keys=True)}"
    )
    if summary["invalid_present"]:
        print(
            "present=true but unreadable/missing: "
            + ", ".join(summary["invalid_present"])
        )
    if summary["missing_by_suite"]:
        print(
            "missing by suite: "
            f"{json.dumps(summary['missing_by_suite'], sort_keys=True)}"
        )


def _is_readable_file(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        with path.open("rb") as stream:
            stream.read(1)
    except OSError:
        return False
    return True


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check DUM-E regression media status")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--suite", default=None, help="optional suite filter")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="fail if required_for_phase5 clips are missing or present clips are unreadable",
    )
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
