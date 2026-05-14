from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from manuals.color_detector import (
    classify_color_components,
    detect_block_requirements,
    detect_color_regions,
    detect_color_regions_debug,
    parse_region,
)
from manuals.visual_debug import has_preview_backend, save_preview


def test_parse_region_supports_pixel_and_normalized_coordinates() -> None:
    pixel_region = parse_region("10,20,30,40")
    normalized_region = parse_region("0.13,0.36,0.62,0.77", normalized=True)

    assert pixel_region.resolve((100, 200)).bbox == (10, 20, 30, 40)
    assert normalized_region.resolve((100, 200)).bbox == (26, 36, 124, 77)

    with pytest.raises(ValueError, match="whole numbers"):
        parse_region("0.1,0.2,0.3,0.4")


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


def test_include_and_exclude_regions_mask_detection_area() -> None:
    image = np.full((80, 120, 3), (0, 255, 255), dtype=np.uint8)
    image[10:30, 10:30] = (255, 0, 0)
    image[10:30, 60:80] = (0, 0, 255)

    include_left = [parse_region("0,0,50,80")]
    left_regions = detect_color_regions(
        image,
        min_region_area=50,
        include_regions=include_left,
    )

    assert [region.color for region in left_regions] == ["red"]

    include_both = [parse_region("0,0,100,80")]
    exclude_red = [parse_region("5,5,35,35")]
    masked_regions = detect_color_regions(
        image,
        min_region_area=50,
        include_regions=include_both,
        exclude_regions=exclude_red,
    )

    assert [region.color for region in masked_regions] == ["blue"]


def test_reject_thin_components_keeps_block_like_regions() -> None:
    image = np.full((80, 120, 3), (0, 255, 255), dtype=np.uint8)
    image[10:30, 10:30] = (255, 0, 0)
    image[50:52, 10:100] = (255, 0, 0)

    debug_result = detect_color_regions_debug(
        image,
        min_region_area=20,
        reject_thin_components=True,
    )

    assert [region.bbox for region in debug_result.regions] == [(10, 10, 30, 30)]
    assert debug_result.rejected_regions
    assert debug_result.rejected_regions[0].role in {"ARROW", "UNKNOWN"}


def test_large_white_background_region_is_rejected() -> None:
    image = np.full((80, 120, 3), (255, 255, 255), dtype=np.uint8)
    image[10:30, 10:30] = (255, 0, 0)

    debug_result = detect_color_regions_debug(image, min_region_area=50)

    assert [region.color for region in debug_result.regions] == ["red"]
    assert [(region.color, region.rejection_reason) for region in debug_result.rejected_regions] == [
        ("white", "background")
    ]


def test_arrow_shaped_blue_component_is_rejected_but_blue_block_is_active() -> None:
    image = _new_piece_scene()
    image[10:30, 15:35] = (0, 0, 255)

    debug_result = classify_color_components(image, min_region_area=20, mode="new-pieces")

    blue_regions = [region for region in debug_result.regions if region.color == "blue"]
    rejected_blue_roles = [
        region.role for region in debug_result.rejected_regions if region.color == "blue"
    ]

    assert [region.bbox for region in blue_regions] == [(15, 10, 35, 30)]
    assert "ARROW" in rejected_blue_roles


def test_text_like_black_component_is_rejected_but_black_block_is_active() -> None:
    image = _new_piece_scene()
    image[10:30, 15:35] = (0, 0, 0)
    image[5:45, 95:100] = (0, 0, 0)
    image[5:10, 95:115] = (0, 0, 0)
    image[40:45, 95:115] = (0, 0, 0)

    debug_result = classify_color_components(image, min_region_area=20, mode="new-pieces")

    black_regions = [region for region in debug_result.regions if region.color == "black"]
    rejected_black_roles = [
        region.role for region in debug_result.rejected_regions if region.color == "black"
    ]

    assert [region.bbox for region in black_regions] == [(15, 10, 35, 30)]
    assert "TEXT" in rejected_black_roles


def test_small_active_white_block_can_remain_valid() -> None:
    image = np.full((100, 140, 3), (200, 200, 200), dtype=np.uint8)
    image[10:30, 15:35] = (255, 255, 255)
    _draw_blue_arrow(image)

    debug_result = classify_color_components(image, min_region_area=20, mode="new-pieces")

    assert [region.color for region in debug_result.regions] == ["white"]


def test_dimmed_low_saturation_old_assembly_is_rejected_in_new_piece_mode() -> None:
    image = _new_piece_scene()
    image[65:90, 20:70] = (175, 190, 175)

    debug_result = classify_color_components(image, min_region_area=20, mode="new-pieces")

    assert [region.color for region in debug_result.regions] == ["green"]
    assert any(region.role == "DIMMED_OLD_BLOCK" for region in debug_result.rejected_regions)


def test_no_arrow_page_keeps_saturated_blocks_and_rejects_pale_blue_old_blocks() -> None:
    image = np.full((120, 160, 3), (255, 255, 255), dtype=np.uint8)
    image[10:35, 10:45] = (210, 60, 30)
    image[45:75, 12:48] = (45, 150, 35)
    image[82:108, 20:55] = (165, 190, 225)

    debug_result = classify_color_components(image, min_region_area=20, mode="new-pieces")
    active_colors = {region.color for region in debug_result.regions}
    rejected = {(region.color, region.role) for region in debug_result.rejected_regions}

    assert active_colors == {"red", "green"}
    assert ("blue", "DIMMED_OLD_BLOCK") in rejected
    assert debug_result.status == "ok_no_arrow_detected"


def test_no_arrow_page_with_active_block_returns_ok_no_arrow_detected() -> None:
    image = np.full((80, 120, 3), (255, 255, 255), dtype=np.uint8)
    image[10:30, 10:30] = (0, 128, 0)

    debug_result = classify_color_components(image, min_region_area=20, mode="new-pieces")

    assert [region.color for region in debug_result.regions] == ["green"]
    assert debug_result.status == "ok_no_arrow_detected"
    assert "no arrows detected" in (debug_result.warnings or [])


def test_no_arrow_page_without_active_candidates_returns_no_new_piece_indicator() -> None:
    image = np.full((80, 120, 3), (255, 255, 255), dtype=np.uint8)

    debug_result = classify_color_components(image, min_region_area=20, mode="new-pieces")

    assert debug_result.regions == []
    assert debug_result.status == "no_new_piece_indicator"
    assert "no arrows detected" in (debug_result.warnings or [])


def test_visible_blocks_mode_counts_without_arrow_indicator() -> None:
    image = np.full((80, 120, 3), (255, 255, 255), dtype=np.uint8)
    image[10:30, 10:30] = (0, 128, 0)

    debug_result = classify_color_components(image, min_region_area=20, mode="visible-blocks")

    assert [region.color for region in debug_result.regions] == ["green"]


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


def _new_piece_scene() -> np.ndarray:
    image = np.full((100, 140, 3), (255, 255, 255), dtype=np.uint8)
    image[10:30, 15:35] = (0, 160, 0)
    _draw_blue_arrow(image)
    return image


def _draw_blue_arrow(image: np.ndarray) -> None:
    image[35:70, 80:84] = (0, 0, 255)
    image[66:74, 76:88] = (0, 0, 255)
