from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np

from manuals.types import BlockRequirement, ComponentRole, DetectedColorRegion, ReaderMode


@dataclass(frozen=True)
class ColorThreshold:
    hue_min: float | None = None
    hue_max: float | None = None
    saturation_min: float | None = None
    saturation_max: float | None = None
    value_min: float | None = None
    value_max: float | None = None
    wraps_hue: bool = False


@dataclass(frozen=True)
class ImageRegion:
    bbox: tuple[int, int, int, int]


@dataclass(frozen=True)
class RegionSpec:
    x1: float
    y1: float
    x2: float
    y2: float
    normalized: bool = False

    def resolve(self, image_shape: Sequence[int]) -> ImageRegion:
        height, width = _image_height_width(image_shape)
        if self.normalized:
            x_min = math.floor(self.x1 * width)
            y_min = math.floor(self.y1 * height)
            x_max = math.ceil(self.x2 * width)
            y_max = math.ceil(self.y2 * height)
        else:
            x_min = int(self.x1)
            y_min = int(self.y1)
            x_max = int(self.x2)
            y_max = int(self.y2)

        x_min = max(0, min(width, x_min))
        y_min = max(0, min(height, y_min))
        x_max = max(0, min(width, x_max))
        y_max = max(0, min(height, y_max))
        if x_max <= x_min or y_max <= y_min:
            raise ValueError("manual color detection region is empty after clipping")
        return ImageRegion((x_min, y_min, x_max, y_max))


@dataclass(frozen=True)
class ColorDetectionDebugResult:
    regions: list[DetectedColorRegion]
    rejected_regions: list[DetectedColorRegion]
    include_regions: list[ImageRegion]
    exclude_regions: list[ImageRegion]
    mode: ReaderMode = "visible-blocks"
    status: str = "ok"
    warnings: list[str] | None = None


@dataclass(frozen=True)
class _ColorSetSummary:
    color: str
    component_count: int
    total_area: int
    compact_count: int
    mean_saturation: float
    mean_value: float


def parse_region(value: str, *, normalized: bool = False) -> RegionSpec:
    parts = [part.strip() for part in value.split(",")]
    if len(parts) != 4:
        raise ValueError(f"Region must contain four comma-separated coordinates: {value}")

    try:
        x1, y1, x2, y2 = (float(part) for part in parts)
    except ValueError as exc:
        raise ValueError(f"Region coordinates must be numeric: {value}") from exc

    coordinates = (x1, y1, x2, y2)
    if any(coordinate < 0 for coordinate in coordinates):
        raise ValueError(f"Region coordinates must be non-negative: {value}")
    if normalized and any(coordinate > 1.0 for coordinate in coordinates):
        raise ValueError(f"Normalized region coordinates must be between 0 and 1: {value}")
    if not normalized and any(not coordinate.is_integer() for coordinate in coordinates):
        raise ValueError(f"Pixel region coordinates must be whole numbers: {value}")
    if x2 <= x1 or y2 <= y1:
        raise ValueError(f"Region max coordinates must be greater than min coordinates: {value}")

    return RegionSpec(x1=x1, y1=y1, x2=x2, y2=y2, normalized=normalized)


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

_BACKGROUND_COLORS = {"white", "gray"}
_BACKGROUND_EDGE_AREA_FRACTION = 0.20
_BACKGROUND_INTERIOR_AREA_FRACTION = 0.08
_BACKGROUND_MAX_FILL_RATIO = 0.75
_THIN_ASPECT_RATIO = 8.0
_THIN_FILL_RATIO = 0.22
_THIN_MINOR_DIMENSION = 2
_DARK_TEXT_VALUE_MAX = 0.28
_DIMMED_SATURATION_MAX = 0.35
_DIMMED_VALUE_MIN = 0.45
_ARROW_SATURATION_MIN = 0.30
_BLOCK_MIN_DIMENSION = 5


def detect_block_requirements(
    image: np.ndarray,
    *,
    thresholds: Mapping[str, ColorThreshold] | None = None,
    min_region_area: int = 100,
    max_region_area: int | None = None,
    ignore_colors: set[str] | None = None,
    ignore_hex_colors: set[str] | None = None,
    hex_tolerance: int = 25,
    include_regions: Sequence[RegionSpec] | None = None,
    exclude_regions: Sequence[RegionSpec] | None = None,
    reject_thin_components: bool = False,
    reject_edge_touching: bool = False,
    mode: ReaderMode = "visible-blocks",
) -> list[BlockRequirement]:
    """Detect colored block-like regions from an RGB numpy image."""
    regions = detect_color_regions(
        image,
        thresholds=thresholds,
        min_region_area=min_region_area,
        max_region_area=max_region_area,
        ignore_colors=ignore_colors,
        ignore_hex_colors=ignore_hex_colors,
        hex_tolerance=hex_tolerance,
        include_regions=include_regions,
        exclude_regions=exclude_regions,
        reject_thin_components=reject_thin_components,
        reject_edge_touching=reject_edge_touching,
        mode=mode,
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
    max_region_area: int | None = None,
    ignore_colors: set[str] | None = None,
    ignore_hex_colors: set[str] | None = None,
    hex_tolerance: int = 25,
    include_regions: Sequence[RegionSpec] | None = None,
    exclude_regions: Sequence[RegionSpec] | None = None,
    reject_thin_components: bool = False,
    reject_edge_touching: bool = False,
    mode: ReaderMode = "visible-blocks",
) -> list[DetectedColorRegion]:
    """Detect colored block-like regions and expose bounding boxes for debug previews."""
    return detect_color_regions_debug(
        image,
        thresholds=thresholds,
        min_region_area=min_region_area,
        max_region_area=max_region_area,
        ignore_colors=ignore_colors,
        ignore_hex_colors=ignore_hex_colors,
        hex_tolerance=hex_tolerance,
        include_regions=include_regions,
        exclude_regions=exclude_regions,
        reject_thin_components=reject_thin_components,
        reject_edge_touching=reject_edge_touching,
        mode=mode,
    ).regions


def detect_color_regions_debug(
    image: np.ndarray,
    *,
    thresholds: Mapping[str, ColorThreshold] | None = None,
    min_region_area: int = 100,
    max_region_area: int | None = None,
    ignore_colors: set[str] | None = None,
    ignore_hex_colors: set[str] | None = None,
    hex_tolerance: int = 25,
    include_regions: Sequence[RegionSpec] | None = None,
    exclude_regions: Sequence[RegionSpec] | None = None,
    reject_thin_components: bool = False,
    reject_edge_touching: bool = False,
    mode: ReaderMode = "visible-blocks",
) -> ColorDetectionDebugResult:
    """Detect color regions and retain rejected component boxes for debug previews."""
    return classify_color_components(
        image,
        thresholds=thresholds,
        min_region_area=min_region_area,
        max_region_area=max_region_area,
        ignore_colors=ignore_colors,
        ignore_hex_colors=ignore_hex_colors,
        hex_tolerance=hex_tolerance,
        include_regions=include_regions,
        exclude_regions=exclude_regions,
        reject_thin_components=reject_thin_components,
        reject_edge_touching=reject_edge_touching,
        mode=mode,
    )


def classify_color_components(
    image: np.ndarray,
    *,
    thresholds: Mapping[str, ColorThreshold] | None = None,
    min_region_area: int = 100,
    max_region_area: int | None = None,
    ignore_colors: set[str] | None = None,
    ignore_hex_colors: set[str] | None = None,
    hex_tolerance: int = 25,
    include_regions: Sequence[RegionSpec] | None = None,
    exclude_regions: Sequence[RegionSpec] | None = None,
    reject_thin_components: bool = False,
    reject_edge_touching: bool = False,
    mode: ReaderMode = "new-pieces",
) -> ColorDetectionDebugResult:
    """Classify visible components by role, then expose accepted block components."""
    if mode not in {"new-pieces", "visible-blocks"}:
        raise ValueError(f"Unsupported manual reader mode: {mode}")
    _validate_area_filters(min_region_area, max_region_area)
    rgb = _ensure_rgb_image(image)
    active_mask, resolved_includes, resolved_excludes = _spatial_mask(
        rgb.shape[:2],
        include_regions=include_regions,
        exclude_regions=exclude_regions,
    )
    if not active_mask.any():
        raise ValueError("manual color detection regions leave no pixels to inspect")

    ignored_pixels = _ignored_hex_mask(
        rgb,
        ignore_hex_colors=ignore_hex_colors,
        hex_tolerance=hex_tolerance,
    )
    hue, saturation, value = _rgb_to_hsv_channels(rgb)
    gray = _rgb_to_gray(rgb)
    active_thresholds = thresholds or DEFAULT_THRESHOLDS
    ignored = {color.lower() for color in ignore_colors or set()}
    accepted_regions: list[DetectedColorRegion] = []
    rejected_regions: list[DetectedColorRegion] = []
    active_area = int(np.count_nonzero(active_mask))
    component_id = 0
    candidates: list[DetectedColorRegion] = []

    for color, threshold in active_thresholds.items():
        if color.lower() in ignored:
            continue
        mask = _threshold_mask(hue, saturation, value, threshold)
        mask &= active_mask
        mask &= ~ignored_pixels
        components = _connected_components(mask, active_mask=active_mask)
        for component in components:
            component_id += 1
            metrics = _component_metrics(
                component,
                rgb=rgb,
                hue=hue,
                saturation=saturation,
                value=value,
                gray=gray,
                active_area=active_area,
            )
            role, reason = _initial_component_role(
                component,
                color=color,
                metrics=metrics,
                min_region_area=min_region_area,
                max_region_area=max_region_area,
                reject_thin_components=reject_thin_components,
                reject_edge_touching=reject_edge_touching,
            )
            if reason == "min-area":
                continue
            candidates.append(
                DetectedColorRegion(
                    color=color,
                    bbox=component.bbox,
                    confidence=None,
                    area=component.area,
                    rejection_reason=reason,
                    role=role,
                    component_id=component_id,
                    metrics=metrics,
                )
            )

    arrow_regions = [region for region in candidates if region.role == "ARROW"]
    arrow_found = bool(arrow_regions)
    warnings: list[str] = []

    for candidate in candidates:
        role = candidate.role
        reason = candidate.rejection_reason
        if role == "UNKNOWN":
            role, reason = _block_candidate_role(
                candidate,
                mode=mode,
                arrow_regions=arrow_regions,
            )
        elif mode == "visible-blocks" and role == "DIMMED_OLD_BLOCK":
            role = "ACTIVE_BLOCK"
            reason = None

        region = _replace_region_role(candidate, role=role, reason=reason)
        if role == "ACTIVE_BLOCK":
            accepted_regions.append(region)
        else:
            rejected_regions.append(region)

    confidences = _confidence_by_color(accepted_regions)
    accepted_regions = [
        _replace_region_confidence(region, confidences.get(region.color, 0.0))
        for region in accepted_regions
    ]
    status = _classification_status(
        accepted_regions,
        mode=mode,
        arrow_found=arrow_found,
        warnings=warnings,
    )

    return ColorDetectionDebugResult(
        regions=accepted_regions,
        rejected_regions=rejected_regions,
        include_regions=resolved_includes,
        exclude_regions=resolved_excludes,
        mode=mode,
        status=status,
        warnings=warnings,
    )


def active_color_set(
    accepted_regions: Sequence[DetectedColorRegion],
    rejected_regions: Sequence[DetectedColorRegion] = (),
) -> list[str]:
    """Aggregate classified components into the required active color set."""
    summaries = _color_set_summaries(accepted_regions)
    if not summaries:
        return []

    colors = set(summaries)
    max_color_area = max(summary.total_area for summary in summaries.values())

    for color, summary in summaries.items():
        if _is_minor_artifact_color(color, summary, max_color_area, rejected_regions):
            colors.discard(color)
        elif _is_dimmed_blue_leak(color, summary, rejected_regions):
            colors.discard(color)

    if "yellow" in colors:
        yellow_area = summaries["yellow"].total_area
        for warm_color in ("orange", "red"):
            summary = summaries.get(warm_color)
            if summary is not None and summary.total_area < max(300, yellow_area * 0.04):
                colors.discard(warm_color)

    if "white" in colors and not _has_active_white_evidence(accepted_regions, summaries["white"]):
        colors.discard("white")

    return sorted(colors)


def _color_set_summaries(
    regions: Sequence[DetectedColorRegion],
) -> dict[str, _ColorSetSummary]:
    grouped: dict[str, list[DetectedColorRegion]] = {}
    for region in regions:
        grouped.setdefault(region.color, []).append(region)

    summaries: dict[str, _ColorSetSummary] = {}
    for color, color_regions in grouped.items():
        total_area = sum(_region_area(region) for region in color_regions)
        if total_area <= 0:
            continue
        weighted_saturation = sum(
            float(region.metrics.get("mean_saturation", 0.0)) * _region_area(region)
            for region in color_regions
        )
        weighted_value = sum(
            float(region.metrics.get("mean_value", 0.0)) * _region_area(region)
            for region in color_regions
        )
        summaries[color] = _ColorSetSummary(
            color=color,
            component_count=len(color_regions),
            total_area=total_area,
            compact_count=sum(
                1 for region in color_regions if _is_compact_color_set_region(region)
            ),
            mean_saturation=weighted_saturation / total_area,
            mean_value=weighted_value / total_area,
        )
    return summaries


def _is_minor_artifact_color(
    color: str,
    summary: _ColorSetSummary,
    max_color_area: int,
    rejected_regions: Sequence[DetectedColorRegion],
) -> bool:
    if summary.total_area < 120:
        return True

    same_color_arrow = any(
        region.color == color and region.role == "ARROW" for region in rejected_regions
    )
    if same_color_arrow and summary.total_area < max(1000, max_color_area * 0.03):
        return True

    return False


def _is_dimmed_blue_leak(
    color: str,
    summary: _ColorSetSummary,
    rejected_regions: Sequence[DetectedColorRegion],
) -> bool:
    if color != "blue":
        return False

    same_color_dimmed = any(
        region.color == color and region.role == "DIMMED_OLD_BLOCK"
        for region in rejected_regions
    )
    pale_blue = summary.mean_saturation <= 0.55 and summary.mean_value >= 0.72
    fragmented_blue = summary.component_count >= 8 and summary.compact_count <= 3
    return pale_blue and (same_color_dimmed or fragmented_blue)


def _has_active_white_evidence(
    accepted_regions: Sequence[DetectedColorRegion],
    summary: _ColorSetSummary,
) -> bool:
    compact_white_regions = [
        region
        for region in accepted_regions
        if region.color == "white" and _is_compact_white_region(region)
    ]
    if compact_white_regions:
        return True
    return summary.total_area <= 3000 and summary.compact_count > 0


def _is_compact_color_set_region(region: DetectedColorRegion) -> bool:
    metrics = region.metrics
    return (
        _region_area(region) >= 80
        and int(metrics.get("width", 0)) >= 6
        and int(metrics.get("height", 0)) >= 6
        and float(metrics.get("aspect_ratio", 99.0)) <= 4.0
        and float(metrics.get("fill_ratio", 0.0)) >= 0.35
        and not bool(metrics.get("touches_edge", False))
    )


def _is_compact_white_region(region: DetectedColorRegion) -> bool:
    return _is_compact_color_set_region(region) and _is_compact_white_metrics(
        region.metrics,
        area=_region_area(region),
    )


def _is_compact_white_metrics(
    metrics: dict[str, float | int | str | bool],
    *,
    area: int,
) -> bool:
    return (
        180 <= area <= 2000
        and int(metrics.get("width", 0)) >= 6
        and int(metrics.get("height", 0)) >= 6
        and float(metrics.get("aspect_ratio", 99.0)) <= 3.25
        and float(metrics.get("fill_ratio", 0.0)) >= 0.50
        and float(metrics.get("mean_saturation", 1.0)) <= 0.08
        and float(metrics.get("mean_value", 0.0)) >= 0.90
        and float(metrics.get("edge_contrast", 0.0)) >= 0.015
        and not bool(metrics.get("touches_edge", False))
    )


def _region_area(region: DetectedColorRegion) -> int:
    if region.area is not None:
        return region.area
    metric_area = region.metrics.get("area")
    if isinstance(metric_area, int | float):
        return int(metric_area)
    x_min, y_min, x_max, y_max = region.bbox
    return max(0, x_max - x_min) * max(0, y_max - y_min)


@dataclass(frozen=True)
class _ColorComponent:
    area: int
    bbox: tuple[int, int, int, int]
    touches_active_edge: bool
    pixels: tuple[tuple[int, int], ...]


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


def _validate_area_filters(min_region_area: int, max_region_area: int | None) -> None:
    if min_region_area < 1:
        raise ValueError("min area must be positive")
    if max_region_area is not None and max_region_area < 1:
        raise ValueError("max area must be positive")


def _spatial_mask(
    image_shape: Sequence[int],
    *,
    include_regions: Sequence[RegionSpec] | None,
    exclude_regions: Sequence[RegionSpec] | None,
) -> tuple[np.ndarray, list[ImageRegion], list[ImageRegion]]:
    height, width = _image_height_width(image_shape)
    resolved_includes = [region.resolve((height, width)) for region in include_regions or ()]
    resolved_excludes = [region.resolve((height, width)) for region in exclude_regions or ()]

    if resolved_includes:
        mask = np.zeros((height, width), dtype=bool)
        for region in resolved_includes:
            x_min, y_min, x_max, y_max = region.bbox
            mask[y_min:y_max, x_min:x_max] = True
    else:
        mask = np.ones((height, width), dtype=bool)

    for region in resolved_excludes:
        x_min, y_min, x_max, y_max = region.bbox
        mask[y_min:y_max, x_min:x_max] = False

    return mask, resolved_includes, resolved_excludes


def _image_height_width(image_shape: Sequence[int]) -> tuple[int, int]:
    if len(image_shape) < 2:
        raise ValueError("manual color detection expects image shape with height and width")
    height = int(image_shape[0])
    width = int(image_shape[1])
    if height <= 0 or width <= 0:
        raise ValueError("manual color detection expects a non-empty image")
    return height, width


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


def _rgb_to_gray(rgb: np.ndarray) -> np.ndarray:
    return rgb[:, :, 0] * 0.299 + rgb[:, :, 1] * 0.587 + rgb[:, :, 2] * 0.114


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


def _connected_components(mask: np.ndarray, *, active_mask: np.ndarray) -> list[_ColorComponent]:
    visited = np.zeros(mask.shape, dtype=bool)
    components: list[_ColorComponent] = []
    height, width = mask.shape

    for row in range(height):
        for column in range(width):
            if visited[row, column] or not mask[row, column]:
                continue
            components.append(_flood_fill_component(mask, active_mask, visited, row, column))

    return components


def _flood_fill_component(
    mask: np.ndarray,
    active_mask: np.ndarray,
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
    touches_active_edge = False
    pixels: list[tuple[int, int]] = []

    while stack:
        current_row, current_column = stack.pop()
        area += 1
        pixels.append((current_row, current_column))
        if _touches_inactive_neighbor(active_mask, current_row, current_column):
            touches_active_edge = True
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
        touches_active_edge=touches_active_edge,
        pixels=tuple(pixels),
    )


def _touches_inactive_neighbor(active_mask: np.ndarray, row: int, column: int) -> bool:
    height, width = active_mask.shape
    for next_row, next_column in (
        (row - 1, column),
        (row + 1, column),
        (row, column - 1),
        (row, column + 1),
    ):
        if not (0 <= next_row < height and 0 <= next_column < width):
            return True
        if not active_mask[next_row, next_column]:
            return True
    return False


def _component_metrics(
    component: _ColorComponent,
    *,
    rgb: np.ndarray,
    hue: np.ndarray,
    saturation: np.ndarray,
    value: np.ndarray,
    gray: np.ndarray,
    active_area: int,
) -> dict[str, float | int | str | bool]:
    x_min, y_min, x_max, y_max = component.bbox
    rows = np.asarray([pixel[0] for pixel in component.pixels], dtype=int)
    columns = np.asarray([pixel[1] for pixel in component.pixels], dtype=int)
    width = x_max - x_min
    height = y_max - y_min
    bbox_area = max(1, width * height)
    rgb_patch = rgb[rows, columns]
    mean_rgb = np.mean(rgb_patch, axis=0)
    perimeter = _component_perimeter(component)

    return {
        "area": component.area,
        "contour_area": component.area,
        "contour_complexity": (perimeter * perimeter) / max(1, component.area),
        "perimeter": perimeter,
        "width": width,
        "height": height,
        "aspect_ratio": max(width, height) / max(1, min(width, height)),
        "fill_ratio": component.area / bbox_area,
        "area_fraction": component.area / max(1, active_area),
        "center_x": (x_min + x_max) / 2,
        "center_y": (y_min + y_max) / 2,
        "mean_red": float(mean_rgb[0]),
        "mean_green": float(mean_rgb[1]),
        "mean_blue": float(mean_rgb[2]),
        "mean_hue": float(np.mean(hue[rows, columns])),
        "mean_saturation": float(np.mean(saturation[rows, columns])),
        "mean_value": float(np.mean(value[rows, columns])),
        "edge_contrast": _edge_contrast(gray, component.bbox),
        "touches_edge": component.touches_active_edge,
    }


def _component_perimeter(component: _ColorComponent) -> int:
    pixels = set(component.pixels)
    perimeter = 0
    for row, column in component.pixels:
        for next_row, next_column in (
            (row - 1, column),
            (row + 1, column),
            (row, column - 1),
            (row, column + 1),
        ):
            if (next_row, next_column) not in pixels:
                perimeter += 1
    return perimeter


def _edge_contrast(gray: np.ndarray, bbox: tuple[int, int, int, int]) -> float:
    x_min, y_min, x_max, y_max = bbox
    height, width = gray.shape
    inner = gray[y_min:y_max, x_min:x_max]
    if inner.size == 0:
        return 0.0

    pad_x_min = max(0, x_min - 1)
    pad_y_min = max(0, y_min - 1)
    pad_x_max = min(width, x_max + 1)
    pad_y_max = min(height, y_max + 1)
    outer = gray[pad_y_min:pad_y_max, pad_x_min:pad_x_max]
    if outer.size == inner.size:
        return 0.0
    return float(abs(np.mean(inner) - np.mean(outer)))


def _initial_component_role(
    component: _ColorComponent,
    *,
    color: str,
    metrics: dict[str, float | int | str | bool],
    min_region_area: int,
    max_region_area: int | None,
    reject_thin_components: bool,
    reject_edge_touching: bool,
) -> tuple[ComponentRole, str | None]:
    if component.area < min_region_area:
        return "UNKNOWN", "min-area"
    if max_region_area is not None and component.area > max_region_area:
        return "BACKGROUND", "max-area"
    if _is_large_background_component(
        component,
        color=color,
        active_area=int(component.area / max(float(metrics["area_fraction"]), 1e-9)),
    ):
        return "BACKGROUND", "background"
    if _is_interior_background_like(color=color, metrics=metrics):
        return "BACKGROUND", "background"
    if _is_arrow_like(component, metrics):
        return "ARROW", "arrow-shape"
    if _is_text_like(component, color=color, metrics=metrics):
        return "TEXT", "text-like"
    if reject_edge_touching and component.touches_active_edge:
        return "BACKGROUND", "edge-touching"
    if reject_thin_components and _is_thin_component(component):
        return "UNKNOWN", "thin"
    return "UNKNOWN", None


def _block_candidate_role(
    candidate: DetectedColorRegion,
    *,
    mode: ReaderMode,
    arrow_regions: list[DetectedColorRegion],
) -> tuple[ComponentRole, str | None]:
    if not _is_block_like_region(candidate):
        return "UNKNOWN", candidate.rejection_reason or "not-block-shaped"
    if mode == "new-pieces" and _is_dimmed_old_region(candidate, arrow_regions):
        return "DIMMED_OLD_BLOCK", "dimmed-old-block"
    return "ACTIVE_BLOCK", None


def _classification_status(
    accepted_regions: list[DetectedColorRegion],
    *,
    mode: ReaderMode,
    arrow_found: bool,
    warnings: list[str],
) -> str:
    if mode != "new-pieces":
        return "ok"
    if arrow_found:
        return "ok"
    warnings.append("no arrows detected")
    if accepted_regions:
        return "ok_no_arrow_detected"
    return "no_new_piece_indicator"


def _is_arrow_like(
    component: _ColorComponent,
    metrics: dict[str, float | int | str | bool],
) -> bool:
    major_dimension = max(int(metrics["width"]), int(metrics["height"]))
    minor_dimension = min(int(metrics["width"]), int(metrics["height"]))
    return (
        float(metrics["mean_saturation"]) >= _ARROW_SATURATION_MIN
        and major_dimension >= 24
        and (
            float(metrics["aspect_ratio"]) >= 5.0
            or (minor_dimension <= 8 and major_dimension >= 20)
            or (float(metrics["aspect_ratio"]) >= 2.8 and float(metrics["fill_ratio"]) <= 0.58)
        )
        and component.area >= 20
    )


def _is_interior_background_like(
    *,
    color: str,
    metrics: dict[str, float | int | str | bool],
) -> bool:
    if color == "white" and _is_compact_white_metrics(metrics, area=int(metrics["area"])):
        return False
    return (
        color.lower() in _BACKGROUND_COLORS
        and int(metrics["area"]) >= 200
        and float(metrics["mean_saturation"]) <= 0.20
        and float(metrics["fill_ratio"]) <= _BACKGROUND_MAX_FILL_RATIO
    )


def _is_text_like(
    component: _ColorComponent,
    *,
    color: str,
    metrics: dict[str, float | int | str | bool],
) -> bool:
    if color.lower() not in {"black", "gray"} and float(metrics["mean_value"]) > _DARK_TEXT_VALUE_MAX:
        return False

    fill_ratio = float(metrics["fill_ratio"])
    area_fraction = float(metrics["area_fraction"])
    top_label_zone = float(metrics["center_y"]) < 0.35 * _component_image_height(component, metrics)
    dark = float(metrics["mean_value"]) <= _DARK_TEXT_VALUE_MAX
    minor_dimension = min(int(metrics["width"]), int(metrics["height"]))
    stroke_like = _is_thin_component(component) or fill_ratio <= 0.58 or minor_dimension <= 6
    label_like = top_label_zone and area_fraction <= 0.08 and fill_ratio <= 0.82
    return dark and (stroke_like or label_like)


def _component_image_height(
    component: _ColorComponent,
    metrics: dict[str, float | int | str | bool],
) -> float:
    area_fraction = max(float(metrics["area_fraction"]), 1e-9)
    estimated_active_area = component.area / area_fraction
    return max(float(metrics["height"]), estimated_active_area**0.5)


def _is_block_like_region(region: DetectedColorRegion) -> bool:
    metrics = region.metrics
    return (
        int(metrics["width"]) >= _BLOCK_MIN_DIMENSION
        and int(metrics["height"]) >= _BLOCK_MIN_DIMENSION
        and float(metrics["aspect_ratio"]) <= 5.0
        and float(metrics["fill_ratio"]) >= 0.28
    )


def _is_dimmed_old_region(
    region: DetectedColorRegion,
    arrow_regions: list[DetectedColorRegion],
) -> bool:
    metrics = region.metrics
    mean_saturation = float(metrics["mean_saturation"])
    mean_value = float(metrics["mean_value"])
    if mean_saturation > _DIMMED_SATURATION_MAX or mean_value < _DIMMED_VALUE_MIN:
        return False

    destination_y = max((float(arrow.metrics["center_y"]) for arrow in arrow_regions), default=0.0)
    below_arrow_destination = bool(arrow_regions) and float(metrics["center_y"]) >= destination_y
    large_washed_region = float(metrics["area_fraction"]) >= 0.04
    compact_white_candidate = (
        region.color == "white"
        and _is_compact_white_metrics(metrics, area=_region_area(region))
    )
    return (below_arrow_destination or large_washed_region) and not compact_white_candidate


def _replace_region_role(
    region: DetectedColorRegion,
    *,
    role: ComponentRole,
    reason: str | None,
) -> DetectedColorRegion:
    return DetectedColorRegion(
        color=region.color,
        bbox=region.bbox,
        confidence=region.confidence,
        area=region.area,
        rejection_reason=reason,
        role=role,
        component_id=region.component_id,
        metrics=region.metrics,
    )


def _replace_region_confidence(
    region: DetectedColorRegion,
    confidence: float,
) -> DetectedColorRegion:
    return DetectedColorRegion(
        color=region.color,
        bbox=region.bbox,
        confidence=confidence,
        area=region.area,
        rejection_reason=region.rejection_reason,
        role=region.role,
        component_id=region.component_id,
        metrics=region.metrics,
    )


def _confidence_by_color(regions: list[DetectedColorRegion]) -> dict[str, float]:
    areas_by_color: dict[str, list[int]] = {}
    for region in regions:
        if region.area is not None:
            areas_by_color.setdefault(region.color, []).append(region.area)
    return {
        color: _confidence_for_components(areas)
        for color, areas in areas_by_color.items()
    }


def _component_rejection_reason(
    component: _ColorComponent,
    *,
    color: str,
    min_region_area: int,
    max_region_area: int | None,
    active_area: int,
    reject_thin_components: bool,
    reject_edge_touching: bool,
) -> str | None:
    if component.area < min_region_area:
        return "min-area"
    if max_region_area is not None and component.area > max_region_area:
        return "max-area"
    if _is_large_background_component(component, color=color, active_area=active_area):
        return "background"
    if reject_edge_touching and component.touches_active_edge:
        return "edge"
    if reject_thin_components and _is_thin_component(component):
        return "thin"
    return None


def _is_large_background_component(
    component: _ColorComponent,
    *,
    color: str,
    active_area: int,
) -> bool:
    if color.lower() not in _BACKGROUND_COLORS or active_area <= 0:
        return False

    area_fraction = component.area / active_area
    if component.touches_active_edge and area_fraction >= _BACKGROUND_EDGE_AREA_FRACTION:
        return True
    return (
        area_fraction >= _BACKGROUND_INTERIOR_AREA_FRACTION
        and _component_fill_ratio(component) <= _BACKGROUND_MAX_FILL_RATIO
    )


def _is_thin_component(component: _ColorComponent) -> bool:
    x_min, y_min, x_max, y_max = component.bbox
    width = x_max - x_min
    height = y_max - y_min
    if width <= 0 or height <= 0:
        return True

    minor_dimension = min(width, height)
    major_dimension = max(width, height)
    aspect_ratio = major_dimension / minor_dimension
    return (
        minor_dimension <= _THIN_MINOR_DIMENSION
        or aspect_ratio >= _THIN_ASPECT_RATIO
        or _component_fill_ratio(component) <= _THIN_FILL_RATIO
    )


def _component_fill_ratio(component: _ColorComponent) -> float:
    x_min, y_min, x_max, y_max = component.bbox
    width = x_max - x_min
    height = y_max - y_min
    if width <= 0 or height <= 0:
        return 0.0
    return component.area / (width * height)


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
