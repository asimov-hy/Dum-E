from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np

from manuals.types import BlockRequirement, DetectedColorRegion


@dataclass(frozen=True)
class ColorThreshold:
    hue_min: float | None = None
    hue_max: float | None = None
    saturation_min: float | None = None
    saturation_max: float | None = None
    value_min: float | None = None
    value_max: float | None = None
    wraps_hue: bool = False


DEFAULT_THRESHOLDS: dict[str, ColorThreshold] = {
    "red": ColorThreshold(
        hue_min=345, hue_max=15, saturation_min=0.35, value_min=0.25, wraps_hue=True
    ),
    "orange": ColorThreshold(hue_min=16, hue_max=40, saturation_min=0.35, value_min=0.25),
    "yellow": ColorThreshold(hue_min=41, hue_max=70, saturation_min=0.30, value_min=0.30),
    "green": ColorThreshold(hue_min=71, hue_max=170, saturation_min=0.25, value_min=0.20),
    "blue": ColorThreshold(hue_min=190, hue_max=255, saturation_min=0.25, value_min=0.20),
    "purple": ColorThreshold(hue_min=256, hue_max=325, saturation_min=0.25, value_min=0.20),
    "black": ColorThreshold(value_max=0.16),
    "white": ColorThreshold(saturation_max=0.18, value_min=0.82),
    "gray": ColorThreshold(saturation_max=0.18, value_min=0.18, value_max=0.82),
}


def detect_block_requirements(
    image: np.ndarray,
    *,
    thresholds: Mapping[str, ColorThreshold] | None = None,
    min_region_area: int = 100,
    ignore_colors: set[str] | None = None,
    ignore_hex_colors: set[str] | None = None,
    hex_tolerance: int = 25,
) -> list[BlockRequirement]:
    """Detect colored block-like regions from an RGB numpy image."""
    regions = detect_color_regions(
        image,
        thresholds=thresholds,
        min_region_area=min_region_area,
        ignore_colors=ignore_colors,
        ignore_hex_colors=ignore_hex_colors,
        hex_tolerance=hex_tolerance,
    )
    counts: dict[str, int] = {}
    confidences: dict[str, list[float]] = {}

    for region in regions:
        counts[region.color] = counts.get(region.color, 0) + 1
        if region.confidence is not None:
            confidences.setdefault(region.color, []).append(region.confidence)

    return [
        BlockRequirement(
            color=color,
            quantity=counts[color],
            confidence=_average(confidences.get(color, [])),
        )
        for color in sorted(counts)
    ]


def detect_color_regions(
    image: np.ndarray,
    *,
    thresholds: Mapping[str, ColorThreshold] | None = None,
    min_region_area: int = 100,
    ignore_colors: set[str] | None = None,
    ignore_hex_colors: set[str] | None = None,
    hex_tolerance: int = 25,
) -> list[DetectedColorRegion]:
    """Detect colored block-like regions and expose bounding boxes for debug previews."""
    rgb = _ensure_rgb_image(image)
    ignored_pixels = _ignored_hex_mask(
        rgb,
        ignore_hex_colors=ignore_hex_colors,
        hex_tolerance=hex_tolerance,
    )
    hue, saturation, value = _rgb_to_hsv_channels(rgb)
    active_thresholds = thresholds or DEFAULT_THRESHOLDS
    ignored = {color.lower() for color in ignore_colors or set()}
    regions: list[DetectedColorRegion] = []

    for color, threshold in active_thresholds.items():
        if color.lower() in ignored:
            continue
        mask = _threshold_mask(hue, saturation, value, threshold)
        mask &= ~ignored_pixels
        components = _connected_components(mask, min_region_area=min_region_area)
        component_areas = [component.area for component in components]
        confidence = _confidence_for_components(component_areas)
        for component in components:
            regions.append(
                DetectedColorRegion(
                    color=color,
                    bbox=component.bbox,
                    confidence=confidence,
                )
            )

    return regions


@dataclass(frozen=True)
class _ColorComponent:
    area: int
    bbox: tuple[int, int, int, int]


def _ensure_rgb_image(image: np.ndarray) -> np.ndarray:
    array = np.asarray(image)
    if array.ndim != 3 or array.shape[2] != 3:
        raise ValueError("manual color detection expects an RGB image with shape (height, width, 3)")
    if array.size == 0:
        raise ValueError("manual color detection expects a non-empty image")
    if np.issubdtype(array.dtype, np.floating):
        if array.max() <= 1.0:
            return np.clip(array, 0.0, 1.0)
        return np.clip(array / 255.0, 0.0, 1.0)
    return np.clip(array.astype(np.float32) / 255.0, 0.0, 1.0)


def _ignored_hex_mask(
    rgb: np.ndarray,
    *,
    ignore_hex_colors: set[str] | None,
    hex_tolerance: int,
) -> np.ndarray:
    mask = np.zeros(rgb.shape[:2], dtype=bool)
    if not ignore_hex_colors:
        return mask
    if hex_tolerance < 0:
        raise ValueError("hex tolerance must be non-negative")

    rgb_255 = rgb * 255.0
    for hex_color in ignore_hex_colors:
        target = np.asarray(_parse_hex_color(hex_color), dtype=np.float32)
        distance = np.linalg.norm(rgb_255 - target, axis=2)
        mask |= distance <= hex_tolerance
    return mask


def _parse_hex_color(hex_color: str) -> tuple[int, int, int]:
    value = hex_color.strip()
    if value.startswith("#"):
        value = value[1:]
    if len(value) != 6:
        raise ValueError(f"Invalid hex color: {hex_color}")
    try:
        return (
            int(value[0:2], 16),
            int(value[2:4], 16),
            int(value[4:6], 16),
        )
    except ValueError as exc:
        raise ValueError(f"Invalid hex color: {hex_color}") from exc


def _rgb_to_hsv_channels(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    red = rgb[:, :, 0]
    green = rgb[:, :, 1]
    blue = rgb[:, :, 2]

    max_channel = np.max(rgb, axis=2)
    min_channel = np.min(rgb, axis=2)
    delta = max_channel - min_channel

    hue = np.zeros_like(max_channel)
    nonzero_delta = delta > 1e-6

    red_is_max = (max_channel == red) & nonzero_delta
    green_is_max = (max_channel == green) & nonzero_delta
    blue_is_max = (max_channel == blue) & nonzero_delta

    hue[red_is_max] = ((green[red_is_max] - blue[red_is_max]) / delta[red_is_max]) % 6
    hue[green_is_max] = ((blue[green_is_max] - red[green_is_max]) / delta[green_is_max]) + 2
    hue[blue_is_max] = ((red[blue_is_max] - green[blue_is_max]) / delta[blue_is_max]) + 4
    hue *= 60

    saturation = np.zeros_like(max_channel)
    nonzero_value = max_channel > 1e-6
    saturation[nonzero_value] = delta[nonzero_value] / max_channel[nonzero_value]

    return hue, saturation, max_channel


def _threshold_mask(
    hue: np.ndarray,
    saturation: np.ndarray,
    value: np.ndarray,
    threshold: ColorThreshold,
) -> np.ndarray:
    mask = np.ones(hue.shape, dtype=bool)

    if threshold.hue_min is not None and threshold.hue_max is not None:
        if threshold.wraps_hue:
            mask &= (hue >= threshold.hue_min) | (hue <= threshold.hue_max)
        else:
            mask &= (hue >= threshold.hue_min) & (hue <= threshold.hue_max)
    elif threshold.hue_min is not None:
        mask &= hue >= threshold.hue_min
    elif threshold.hue_max is not None:
        mask &= hue <= threshold.hue_max

    if threshold.saturation_min is not None:
        mask &= saturation >= threshold.saturation_min
    if threshold.saturation_max is not None:
        mask &= saturation <= threshold.saturation_max
    if threshold.value_min is not None:
        mask &= value >= threshold.value_min
    if threshold.value_max is not None:
        mask &= value <= threshold.value_max

    return mask


def _connected_components(mask: np.ndarray, *, min_region_area: int) -> list[_ColorComponent]:
    visited = np.zeros(mask.shape, dtype=bool)
    components: list[_ColorComponent] = []
    height, width = mask.shape

    for row in range(height):
        for column in range(width):
            if visited[row, column] or not mask[row, column]:
                continue
            component = _flood_fill_component(mask, visited, row, column)
            if component.area >= min_region_area:
                components.append(component)

    return components


def _flood_fill_component(
    mask: np.ndarray,
    visited: np.ndarray,
    row: int,
    column: int,
) -> _ColorComponent:
    stack = [(row, column)]
    visited[row, column] = True
    area = 0
    height, width = mask.shape
    min_row = max_row = row
    min_column = max_column = column

    while stack:
        current_row, current_column = stack.pop()
        area += 1
        min_row = min(min_row, current_row)
        max_row = max(max_row, current_row)
        min_column = min(min_column, current_column)
        max_column = max(max_column, current_column)
        for next_row, next_column in (
            (current_row - 1, current_column),
            (current_row + 1, current_column),
            (current_row, current_column - 1),
            (current_row, current_column + 1),
        ):
            if (
                0 <= next_row < height
                and 0 <= next_column < width
                and not visited[next_row, next_column]
                and mask[next_row, next_column]
            ):
                visited[next_row, next_column] = True
                stack.append((next_row, next_column))

    return _ColorComponent(
        area=area,
        bbox=(min_column, min_row, max_column + 1, max_row + 1),
    )


def _confidence_for_components(areas: list[int]) -> float:
    if not areas:
        return 0.0
    if len(areas) == 1:
        return 0.75

    average_area = sum(areas) / len(areas)
    if average_area == 0:
        return 0.0
    spread = max(abs(area - average_area) / average_area for area in areas)
    return max(0.55, min(0.9, 0.9 - spread * 0.25))


def _average(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)
