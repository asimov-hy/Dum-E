from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import numpy as np

from manuals.color_detector import detect_color_regions
from manuals.types import BlockRequirement, DetectedColorRegion, ManualStageResult


IMAGE_EXTENSIONS = {".bmp", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp"}


class ImageLoadError(RuntimeError):
    """Raised when manual image files cannot be loaded by an available backend."""


def read_manual(
    input_dir: str | Path,
    *,
    stage_id: str = "next",
    ignore_colors: set[str] | None = None,
    ignore_hex_colors: set[str] | None = None,
    hex_tolerance: int = 25,
) -> ManualStageResult:
    directory = Path(input_dir)
    notes: list[str] = []

    if not directory.exists():
        return ManualStageResult(
            stage_id=stage_id,
            notes=[f"Input directory does not exist: {directory}"],
        )
    if not directory.is_dir():
        return ManualStageResult(
            stage_id=stage_id,
            notes=[f"Input path is not a directory: {directory}"],
        )

    image_paths = sorted(
        path for path in directory.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )
    if not image_paths:
        return ManualStageResult(
            stage_id=stage_id,
            notes=[f"No manual images found in {directory}"],
        )

    selected_paths, selection_notes = _select_stage_images(image_paths, stage_id)
    notes.extend(selection_notes)

    totals: dict[str, int] = defaultdict(int)
    confidences: dict[str, list[float]] = defaultdict(list)
    source_images: list[str] = []
    detected_regions: list[DetectedColorRegion] = []

    for image_path in selected_paths:
        image = load_image(image_path)
        source_images.append(str(image_path))
        regions = detect_color_regions(
            image,
            ignore_colors=ignore_colors,
            ignore_hex_colors=ignore_hex_colors,
            hex_tolerance=hex_tolerance,
        )
        detected_regions.extend(regions)
        for region in regions:
            totals[region.color] += 1
            if region.confidence is not None:
                confidences[region.color].append(region.confidence)

    blocks = [
        BlockRequirement(
            color=color,
            quantity=quantity,
            confidence=_average(confidences[color]),
        )
        for color, quantity in sorted(totals.items())
    ]

    if blocks:
        notes.append("Counts are best-effort estimates from color regions.")
    else:
        notes.append("No colored block regions were detected.")

    return ManualStageResult(
        stage_id=stage_id,
        blocks=blocks,
        source_images=source_images,
        notes=notes,
        detected_regions=detected_regions,
    )


def load_image(path: str | Path) -> np.ndarray:
    image_path = Path(path)
    cv2_image = _load_with_cv2(image_path)
    if cv2_image is not None:
        return cv2_image

    pil_image = _load_with_pil(image_path)
    if pil_image is not None:
        return pil_image

    raise ImageLoadError(
        "Unable to load manual image files. Install OpenCV or Pillow to use the manual reader "
        "CLI with image paths."
    )


def _select_stage_images(image_paths: list[Path], stage_id: str) -> tuple[list[Path], list[str]]:
    if stage_id == "next":
        return [image_paths[0]], [f"Stage 'next' selected first image by filename: {image_paths[0].name}"]

    matching_paths = [path for path in image_paths if stage_id.lower() in path.stem.lower()]
    if matching_paths:
        return matching_paths, [f"Stage '{stage_id}' selected {len(matching_paths)} matching image(s)."]

    return [
        image_paths[0]
    ], [f"No image matched stage '{stage_id}'; selected first image by filename: {image_paths[0].name}"]


def _load_with_cv2(path: Path) -> np.ndarray | None:
    try:
        import cv2  # type: ignore[import-not-found]
    except ImportError:
        return None

    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise ImageLoadError(f"Unable to load manual image: {path}")
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


def _load_with_pil(path: Path) -> np.ndarray | None:
    try:
        from PIL import Image  # type: ignore[import-not-found]
    except ImportError:
        return None

    try:
        with Image.open(path) as image:
            return np.asarray(image.convert("RGB"))
    except OSError as exc:
        raise ImageLoadError(f"Unable to load manual image: {path}") from exc


def _average(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)
