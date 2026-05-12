from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from manuals.color_detector import detect_block_requirements, detect_color_regions
from manuals.visual_debug import has_preview_backend, save_preview


def test_detects_red_blue_yellow_blocks_from_rectangles() -> None:
    image = np.full((80, 120, 3), (0, 255, 255), dtype=np.uint8)
    image[10:30, 10:30] = (255, 0, 0)
    image[10:30, 40:60] = (0, 0, 255)
    image[10:30, 70:90] = (255, 255, 0)

    requirements = detect_block_requirements(image, min_region_area=50)
    counts = {requirement.color: requirement.quantity for requirement in requirements}

    assert counts["red"] == 1
    assert counts["blue"] == 1
    assert counts["yellow"] == 1


def test_aggregates_repeated_color_regions() -> None:
    image = np.full((80, 120, 3), (0, 255, 255), dtype=np.uint8)
    image[10:30, 10:30] = (255, 0, 0)
    image[10:30, 40:60] = (255, 0, 0)
    image[40:60, 10:30] = (0, 128, 0)

    requirements = detect_block_requirements(image, min_region_area=50)
    counts = {requirement.color: requirement.quantity for requirement in requirements}

    assert counts["red"] == 2
    assert counts["green"] == 1


def test_ignore_color_removes_color_from_counts() -> None:
    image = np.full((80, 120, 3), (0, 255, 255), dtype=np.uint8)
    image[10:30, 10:30] = (255, 0, 0)
    image[10:30, 40:60] = (0, 0, 255)

    requirements = detect_block_requirements(image, min_region_area=50, ignore_colors={"red"})
    counts = {requirement.color: requirement.quantity for requirement in requirements}

    assert "red" not in counts
    assert counts["blue"] == 1


def test_ignore_hex_removes_background_color_from_counts() -> None:
    image = np.full((80, 120, 3), (34, 34, 34), dtype=np.uint8)
    image[10:30, 10:30] = (255, 0, 0)

    requirements = detect_block_requirements(
        image,
        min_region_area=50,
        ignore_hex_colors={"#222222"},
        hex_tolerance=5,
    )
    counts = {requirement.color: requirement.quantity for requirement in requirements}

    assert counts == {"red": 1}


def test_ignore_hex_colors_do_not_produce_detected_regions() -> None:
    image = np.full((80, 120, 3), (255, 255, 255), dtype=np.uint8)
    image[10:30, 10:30] = (0, 0, 255)

    regions = detect_color_regions(
        image,
        min_region_area=50,
        ignore_hex_colors={"#ffffff"},
        hex_tolerance=0,
    )

    assert [region.color for region in regions] == ["blue"]


def test_preview_generation_writes_synthetic_image_when_backend_available(tmp_path: Path) -> None:
    if not has_preview_backend():
        pytest.skip("OpenCV or Pillow is required for preview generation")

    image = np.full((80, 120, 3), (240, 240, 240), dtype=np.uint8)
    image[10:30, 10:30] = (255, 0, 0)
    image[10:30, 40:60] = (0, 0, 255)
    regions = detect_color_regions(image, min_region_area=50)
    preview_path = tmp_path / "preview.png"

    saved_path = save_preview(image, regions, preview_path)

    assert saved_path == preview_path
    assert preview_path.exists()
    assert preview_path.stat().st_size > 0
