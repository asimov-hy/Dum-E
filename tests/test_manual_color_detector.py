from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from manuals.color_detector import (
    active_color_set,
    classify_color_components,
    detect_block_requirements,
    detect_color_regions,
    detect_color_regions_debug,
    parse_region,
)
from manuals.types import ComponentRole, DetectedColorRegion
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


def test_active_color_set_rejects_blue_arrow_fragments_without_banning_blue() -> None:
    green_block = _region("green", area=5000)
    blue_fragment = _region("blue", area=300, bbox=(40, 10, 50, 40), saturation=0.95)
    rejected_arrow = _region("blue", area=1800, role="ARROW", bbox=(60, 10, 85, 110))
    blue_block = _region("blue", area=800, bbox=(10, 10, 38, 38), saturation=0.9)

    assert active_color_set([green_block, blue_fragment], [rejected_arrow]) == ["green"]
    assert active_color_set([blue_block], []) == ["blue"]


def test_active_color_set_rejects_pale_blue_old_assembly() -> None:
    green_block = _region("green", area=5000)
    pale_blue = _region("blue", area=3000, saturation=0.32, value=0.88)
    rejected_dimmed_blue = _region(
        "blue",
        area=1200,
        role="DIMMED_OLD_BLOCK",
        saturation=0.30,
        value=0.86,
    )

    assert active_color_set([green_block, pale_blue], [rejected_dimmed_blue]) == ["green"]


def test_active_color_set_preserves_compact_white_blocks_and_rejects_white_background() -> None:
    green_block = _region("green", area=5000)
    white_block = _region(
        "white",
        area=500,
        bbox=(20, 20, 62, 39),
        saturation=0.01,
        value=0.98,
        edge_contrast=0.05,
    )
    white_background = _region(
        "white",
        area=14000,
        bbox=(20, 20, 160, 160),
        saturation=0.01,
        value=0.99,
        edge_contrast=0.002,
    )

    assert active_color_set([green_block, white_block], []) == ["green", "white"]
    assert active_color_set([green_block, white_background], []) == ["green"]


def test_active_color_set_does_not_add_white_from_rejected_components() -> None:
    green_block = _region("green", area=5000)
    rejected_white = _region(
        "white",
        area=600,
        role="BACKGROUND",
        bbox=(20, 20, 63, 39),
        saturation=0.01,
        value=0.98,
        edge_contrast=0.05,
    )

    assert active_color_set([green_block], [rejected_white]) == ["green"]


def test_active_color_set_preserves_small_red_and_orange_next_to_yellow() -> None:
    yellow_block = _region("yellow", area=5000, bbox=(10, 10, 90, 90))
    red_block = _region("red", area=400, bbox=(100, 10, 120, 30), saturation=0.95)
    orange_block = _region("orange", area=400, bbox=(100, 40, 120, 60), saturation=0.95)

    assert active_color_set([yellow_block, red_block], []) == ["red", "yellow"]
    assert active_color_set([yellow_block, orange_block], []) == ["orange", "yellow"]


def test_compact_white_block_like_component_is_classified_active() -> None:
    image = np.full((100, 140, 3), (180, 180, 180), dtype=np.uint8)
    image[30:50, 35:78] = (255, 255, 255)

    debug_result = classify_color_components(image, min_region_area=20, mode="new-pieces")

    assert active_color_set(debug_result.regions, debug_result.rejected_regions) == ["white"]


def test_large_white_page_background_is_excluded_from_active_colors() -> None:
    image = np.full((100, 140, 3), (255, 255, 255), dtype=np.uint8)
    image[30:55, 35:78] = (0, 160, 0)

    debug_result = classify_color_components(image, min_region_area=20, mode="new-pieces")

    assert active_color_set(debug_result.regions, debug_result.rejected_regions) == ["green"]


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


def _region(
    color: str,
    *,
    area: int,
    role: ComponentRole = "ACTIVE_BLOCK",
    bbox: tuple[int, int, int, int] | None = None,
    saturation: float = 0.8,
    value: float = 0.8,
    edge_contrast: float = 0.08,
) -> DetectedColorRegion:
    actual_bbox = bbox or (10, 10, 60, 60)
    x_min, y_min, x_max, y_max = actual_bbox
    width = x_max - x_min
    height = y_max - y_min
    return DetectedColorRegion(
        color=color,
        bbox=actual_bbox,
        confidence=None,
        area=area,
        role=role,
        metrics={
            "area": area,
            "width": width,
            "height": height,
            "aspect_ratio": max(width, height) / max(1, min(width, height)),
            "fill_ratio": area / max(1, width * height),
            "mean_saturation": saturation,
            "mean_value": value,
            "edge_contrast": edge_contrast,
            "touches_edge": False,
        },
    )
