from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable

import numpy as np

from manuals.types import DetectedColorRegion


class PreviewError(RuntimeError):
    """Raised when no available image backend can write a visual debug preview."""


_OUTLINE_COLORS: dict[str, tuple[int, int, int]] = {
    "red": (255, 0, 0),
    "orange": (255, 140, 0),
    "yellow": (255, 230, 0),
    "green": (0, 170, 70),
    "blue": (0, 105, 255),
    "purple": (150, 65, 210),
    "black": (25, 25, 25),
    "white": (255, 255, 255),
    "gray": (145, 145, 145),
}
_IGNORED_COLOR = (120, 120, 120)
_REJECTED_COLOR = (220, 30, 130)
_INCLUDE_COLOR = (0, 180, 180)
_EXCLUDE_COLOR = (255, 90, 0)


def save_preview(
    image: np.ndarray,
    regions: Iterable[DetectedColorRegion],
    output_path: str | Path,
    *,
    ignored_regions: Iterable[DetectedColorRegion] = (),
    rejected_regions: Iterable[DetectedColorRegion] = (),
    include_regions: Iterable[tuple[int, int, int, int]] = (),
    exclude_regions: Iterable[tuple[int, int, int, int]] = (),
) -> Path:
    """Save an annotated RGB preview using OpenCV or Pillow if either is installed."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    preview = _ensure_uint8_rgb(image).copy()
    region_list = list(regions)
    ignored_region_list = list(ignored_regions)
    rejected_region_list = list(rejected_regions)
    include_region_list = list(include_regions)
    exclude_region_list = list(exclude_regions)

    if _save_with_cv2(
        preview,
        region_list,
        ignored_region_list,
        rejected_region_list,
        include_region_list,
        exclude_region_list,
        path,
    ):
        return path
    if _save_with_pil(
        preview,
        region_list,
        ignored_region_list,
        rejected_region_list,
        include_region_list,
        exclude_region_list,
        path,
    ):
        return path

    raise PreviewError("Unable to save manual preview image. Install OpenCV or Pillow.")


def open_image(path: str | Path) -> bool:
    """Open an image with the platform image viewer, returning False if that fails."""
    image_path = Path(path)
    try:
        if sys.platform == "darwin":
            return _start_opener(["open", str(image_path)])
        if os.name == "nt":
            os.startfile(str(image_path))  # type: ignore[attr-defined]
            return True

        if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
            return False
        for command in _linux_open_commands(image_path):
            if _start_opener(command):
                return True
        return False
    except OSError:
        return False


def has_preview_backend() -> bool:
    return _has_cv2() or _has_pil()


def _linux_open_commands(path: Path) -> list[list[str]]:
    commands: list[list[str]] = []
    xdg_open = shutil.which("xdg-open")
    if xdg_open is not None:
        commands.append([xdg_open, str(path)])
    gio = shutil.which("gio")
    if gio is not None:
        commands.append([gio, "open", str(path)])
    return commands


def _start_opener(command: list[str]) -> bool:
    subprocess.Popen(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return True


def _ensure_uint8_rgb(image: np.ndarray) -> np.ndarray:
    array = np.asarray(image)
    if array.ndim != 3 or array.shape[2] != 3:
        raise ValueError("manual preview expects an RGB image with shape (height, width, 3)")
    if np.issubdtype(array.dtype, np.floating):
        if array.max() <= 1.0:
            return np.clip(array * 255.0, 0.0, 255.0).astype(np.uint8)
        return np.clip(array, 0.0, 255.0).astype(np.uint8)
    return np.clip(array, 0, 255).astype(np.uint8)


def _save_with_cv2(
    image: np.ndarray,
    regions: list[DetectedColorRegion],
    ignored_regions: list[DetectedColorRegion],
    rejected_regions: list[DetectedColorRegion],
    include_regions: list[tuple[int, int, int, int]],
    exclude_regions: list[tuple[int, int, int, int]],
    path: Path,
) -> bool:
    try:
        import cv2  # type: ignore[import-not-found]
    except ImportError:
        return False

    preview = image.copy()
    for region in rejected_regions:
        _draw_cv2_region(
            cv2,
            preview,
            region,
            _REJECTED_COLOR,
            label=_rejected_label(region),
            thickness=1,
        )
    for bbox in include_regions:
        _draw_cv2_box(cv2, preview, bbox, _INCLUDE_COLOR, label="include", thickness=2)
    for bbox in exclude_regions:
        _draw_cv2_box(cv2, preview, bbox, _EXCLUDE_COLOR, label="exclude", thickness=2)
    for region in ignored_regions:
        _draw_cv2_region(cv2, preview, region, _IGNORED_COLOR, label=f"ignored {region.color}")
    for region in regions:
        _draw_cv2_region(cv2, preview, region, _color_for(region.color), label=_accepted_label(region))
    return bool(cv2.imwrite(str(path), cv2.cvtColor(preview, cv2.COLOR_RGB2BGR)))


def _draw_cv2_region(
    cv2: object,
    image: np.ndarray,
    region: DetectedColorRegion,
    color: tuple[int, int, int],
    *,
    label: str,
    thickness: int | None = None,
) -> None:
    if thickness is None:
        thickness = 1 if label.startswith("ignored ") else 2
    _draw_cv2_box(cv2, image, region.bbox, color, label=label, thickness=thickness)


def _draw_cv2_box(
    cv2: object,
    image: np.ndarray,
    bbox: tuple[int, int, int, int],
    color: tuple[int, int, int],
    *,
    label: str,
    thickness: int,
) -> None:
    x_min, y_min, x_max, y_max = bbox
    cv2.rectangle(image, (x_min, y_min), (x_max - 1, y_max - 1), color, thickness)
    label_y = max(10, y_min - 4)
    cv2.putText(
        image,
        label,
        (x_min, label_y),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.4,
        color,
        1,
        cv2.LINE_AA,
    )


def _save_with_pil(
    image: np.ndarray,
    regions: list[DetectedColorRegion],
    ignored_regions: list[DetectedColorRegion],
    rejected_regions: list[DetectedColorRegion],
    include_regions: list[tuple[int, int, int, int]],
    exclude_regions: list[tuple[int, int, int, int]],
    path: Path,
) -> bool:
    try:
        from PIL import Image, ImageDraw  # type: ignore[import-not-found]
    except ImportError:
        return False

    preview = Image.fromarray(image, mode="RGB")
    draw = ImageDraw.Draw(preview)
    for region in rejected_regions:
        _draw_pil_region(draw, region, _REJECTED_COLOR, label=_rejected_label(region), width=1)
    for bbox in include_regions:
        _draw_pil_box(draw, bbox, _INCLUDE_COLOR, label="include", width=2)
    for bbox in exclude_regions:
        _draw_pil_box(draw, bbox, _EXCLUDE_COLOR, label="exclude", width=2)
    for region in ignored_regions:
        _draw_pil_region(draw, region, _IGNORED_COLOR, label=f"ignored {region.color}", width=1)
    for region in regions:
        _draw_pil_region(draw, region, _color_for(region.color), label=_accepted_label(region), width=2)
    preview.save(path)
    return True


def _draw_pil_region(
    draw: object,
    region: DetectedColorRegion,
    color: tuple[int, int, int],
    *,
    label: str,
    width: int,
) -> None:
    _draw_pil_box(draw, region.bbox, color, label=label, width=width)


def _draw_pil_box(
    draw: object,
    bbox: tuple[int, int, int, int],
    color: tuple[int, int, int],
    *,
    label: str,
    width: int,
) -> None:
    x_min, y_min, x_max, y_max = bbox
    draw.rectangle((x_min, y_min, x_max - 1, y_max - 1), outline=color, width=width)
    label_y = max(0, y_min - 12)
    draw.text((x_min, label_y), label, fill=color)


def _rejected_label(region: DetectedColorRegion) -> str:
    role = region.role
    if region.rejection_reason:
        return f"{role} {region.color}: {region.rejection_reason}"
    return f"{role} {region.color}"


def _accepted_label(region: DetectedColorRegion) -> str:
    return f"{region.role} {region.color}"


def _color_for(color: str) -> tuple[int, int, int]:
    return _OUTLINE_COLORS.get(color.lower(), (255, 0, 255))


def _has_cv2() -> bool:
    try:
        import cv2  # noqa: F401  # type: ignore[import-not-found]
    except ImportError:
        return False
    return True


def _has_pil() -> bool:
    try:
        from PIL import Image  # noqa: F401  # type: ignore[import-not-found]
    except ImportError:
        return False
    return True
