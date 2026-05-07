"""Download and verify the MediaPipe gesture recognizer model.

The preferred Phase 5 path is to keep
``data/models/gesture_recognizer.task.sha256`` under version control. When that
checksum file exists, this script verifies both existing and newly downloaded
model files against it and fails clearly on mismatch.
"""

from __future__ import annotations

import argparse
import hashlib
import tempfile
import urllib.request
from pathlib import Path


DEFAULT_URL = (
    "https://storage.googleapis.com/mediapipe-models/gesture_recognizer/"
    "gesture_recognizer/float16/1/gesture_recognizer.task"
)
DEFAULT_OUTPUT = Path("data/models/gesture_recognizer.task")


def main() -> int:
    args = _parse_args()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    expected_sha256 = args.sha256 or _read_checksum_file(output_path)
    if output_path.is_file():
        existing_sha256 = _sha256(output_path)
        if expected_sha256 is not None and existing_sha256.lower() == expected_sha256.lower():
            print(f"Existing model verified at {output_path}")
            print(f"SHA-256: {existing_sha256}")
            return 0
        if expected_sha256 is None:
            print(f"Existing model found at {output_path}")
            print(f"SHA-256: {existing_sha256}")
            print(
                "No expected SHA-256 was provided, so the existing model was "
                "not cryptographically verified."
            )
            return 0
        print(
            "Existing model checksum mismatch; redownloading. "
            f"expected {expected_sha256}, got {existing_sha256}"
        )

    with tempfile.NamedTemporaryFile(delete=False, dir=output_path.parent) as tmp:
        tmp_path = Path(tmp.name)

    try:
        print(f"Downloading {args.url}")
        urllib.request.urlretrieve(args.url, tmp_path)
        actual_sha256 = _sha256(tmp_path)
        print(f"Downloaded SHA-256: {actual_sha256}")

        if expected_sha256 is not None and actual_sha256.lower() != expected_sha256.lower():
            raise RuntimeError(
                "Downloaded model checksum mismatch: "
                f"expected {expected_sha256}, got {actual_sha256}"
            )
        if expected_sha256 is None:
            print(
                "No expected SHA-256 was provided; checksum was reported but "
                "not verified. Save it to data/models/gesture_recognizer.task.sha256 "
                "or pass --sha256 on future downloads."
            )

        tmp_path.replace(output_path)
        print(f"Saved model to {output_path}")
    finally:
        if tmp_path.exists():
            tmp_path.unlink()

    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download MediaPipe gesture model")
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--sha256", default=None, help="expected model SHA-256 digest")
    return parser.parse_args()


def _read_checksum_file(output_path: Path) -> str | None:
    checksum_path = output_path.with_name(output_path.name + ".sha256")
    if not checksum_path.is_file():
        return None
    text = checksum_path.read_text(encoding="utf-8").strip()
    return text.split()[0] if text else None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
