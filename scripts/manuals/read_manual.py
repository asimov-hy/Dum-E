from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from manuals.color_detector import (  # noqa: E402
    RegionSpec,
    classify_color_components,
    parse_region,
)
from manuals.formatter import format_manual_stage_result  # noqa: E402
from manuals.reader import ImageLoadError, load_image, read_manual  # noqa: E402
from manuals.types import DetectedColorRegion, ReaderMode  # noqa: E402
from manuals.visual_debug import PreviewError, open_image, save_preview  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read manual images and extract colored blocks")
    parser.add_argument(
        "--input",
        default="data/manuals/raw",
        help="Directory containing manual image files",
    )
    parser.add_argument(
        "--stage",
        default="next",
        help="Stage selector. Use 'next' for the first image by filename.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Optional directory where extracted text output should be written",
    )
    parser.add_argument(
        "--clear-output-dir",
        action="store_true",
        help="Clear generated manual-reader outputs in --output-dir before writing",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Save and open an annotated visual detection preview",
    )
    parser.add_argument(
        "--preview-output",
        default=None,
        help="Path where the annotated preview image should be written",
    )
    parser.add_argument(
        "--mode",
        choices=("new-pieces", "visible-blocks"),
        default="new-pieces",
        help="Reader mode. new-pieces counts only active/current-step block components.",
    )
    parser.add_argument(
        "--debug-components",
        action="store_true",
        help="Print classified component boxes, roles, and rejection reasons.",
    )
    parser.add_argument(
        "--ignore-color",
        action="append",
        default=[],
        help="Color to ignore during detection. Can be repeated.",
    )
    parser.add_argument(
        "--ignore-hex",
        action="append",
        default=[],
        help="RGB hex color to ignore before detection. Can be repeated.",
    )
    parser.add_argument(
        "--hex-tolerance",
        type=int,
        default=25,
        help="RGB distance tolerance for ignored hex colors.",
    )
    parser.add_argument(
        "--include-region",
        action="append",
        default=[],
        help="Pixel include region as x1,y1,x2,y2. Can be repeated.",
    )
    parser.add_argument(
        "--include-region-pct",
        action="append",
        default=[],
        help="Normalized include region as x1,y1,x2,y2 using 0.0-1.0 image coordinates.",
    )
    parser.add_argument(
        "--exclude-region",
        action="append",
        default=[],
        help="Pixel exclude region as x1,y1,x2,y2. Can be repeated.",
    )
    parser.add_argument(
        "--exclude-region-pct",
        action="append",
        default=[],
        help="Normalized exclude region as x1,y1,x2,y2 using 0.0-1.0 image coordinates.",
    )
    parser.add_argument(
        "--min-area",
        type=int,
        default=100,
        help="Minimum connected-component area to count.",
    )
    parser.add_argument(
        "--max-area",
        type=int,
        default=None,
        help="Maximum connected-component area to count.",
    )
    parser.add_argument(
        "--reject-thin-components",
        action="store_true",
        help="Reject thin or line-like connected components.",
    )
    parser.add_argument(
        "--reject-edge-touching",
        action="store_true",
        help="Reject components touching the active include/exclude mask edge.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    ignore_colors = {color.lower() for color in args.ignore_color}
    ignore_hex_colors = set(args.ignore_hex)
    if args.clear_output_dir and args.output_dir is None:
        print("Manual reader error: --clear-output-dir requires --output-dir")
        return 1
    try:
        include_regions, exclude_regions = _parse_spatial_regions(args)
    except ValueError as exc:
        print(f"Manual reader error: {exc}")
        return 1

    try:
        result = read_manual(
            args.input,
            stage_id=args.stage,
            mode=args.mode,
            ignore_colors=ignore_colors,
            ignore_hex_colors=ignore_hex_colors,
            hex_tolerance=args.hex_tolerance,
            include_regions=include_regions,
            exclude_regions=exclude_regions,
            min_region_area=args.min_area,
            max_region_area=args.max_area,
            reject_thin_components=args.reject_thin_components,
            reject_edge_touching=args.reject_edge_touching,
        )
    except (ImageLoadError, ValueError) as exc:
        print(f"Manual reader error: {exc}")
        return 1

    output = format_manual_stage_result(result)
    print(output)

    if args.debug_components:
        _print_debug_components(result.accepted_components, result.rejected_components)

    if args.output_dir is not None:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        if args.clear_output_dir:
            _clear_generated_outputs(output_dir)
        output_path = output_dir / _output_filename(args.stage)
        output_path.write_text(output + "\n", encoding="utf-8")
        print(f"Output saved to: {output_path}")

    if args.show or args.preview_output is not None:
        preview_path = Path(args.preview_output) if args.preview_output else _temporary_preview_path()
        try:
            _save_and_open_preview(
                result.source_images,
                preview_path,
                args.mode,
                ignore_colors,
                ignore_hex_colors,
                args.hex_tolerance,
                include_regions,
                exclude_regions,
                args.min_area,
                args.max_area,
                args.reject_thin_components,
                args.reject_edge_touching,
                open_preview=args.show,
            )
        except (ImageLoadError, PreviewError, ValueError) as exc:
            print(f"Manual preview error: {exc}")
            return 1

    return 0


def _save_and_open_preview(
    source_images: list[str],
    preview_path: Path,
    mode: ReaderMode,
    ignore_colors: set[str],
    ignore_hex_colors: set[str],
    hex_tolerance: int,
    include_regions: list[RegionSpec],
    exclude_regions: list[RegionSpec],
    min_region_area: int,
    max_region_area: int | None,
    reject_thin_components: bool,
    reject_edge_touching: bool,
    *,
    open_preview: bool,
) -> None:
    if not source_images:
        print("No manual image was selected; preview was not generated.")
        return

    image = load_image(source_images[0])
    debug_result = classify_color_components(
        image,
        ignore_colors=ignore_colors,
        ignore_hex_colors=ignore_hex_colors,
        hex_tolerance=hex_tolerance,
        include_regions=include_regions,
        exclude_regions=exclude_regions,
        min_region_area=min_region_area,
        max_region_area=max_region_area,
        reject_thin_components=reject_thin_components,
        reject_edge_touching=reject_edge_touching,
        mode=mode,
    )

    saved_path = save_preview(
        image,
        debug_result.regions,
        preview_path,
        rejected_regions=debug_result.rejected_regions,
        include_regions=[region.bbox for region in debug_result.include_regions],
        exclude_regions=[region.bbox for region in debug_result.exclude_regions],
    )
    print(f"Preview saved to: {saved_path}")
    if open_preview and not open_image(saved_path):
        print(f"Could not open preview automatically. Open manually at: {saved_path}")


def _parse_spatial_regions(args: argparse.Namespace) -> tuple[list[RegionSpec], list[RegionSpec]]:
    include_regions = [parse_region(value) for value in args.include_region]
    include_regions.extend(
        parse_region(value, normalized=True) for value in args.include_region_pct
    )

    exclude_regions = [parse_region(value) for value in args.exclude_region]
    exclude_regions.extend(
        parse_region(value, normalized=True) for value in args.exclude_region_pct
    )
    return include_regions, exclude_regions


def _print_debug_components(
    accepted_components: list[DetectedColorRegion],
    rejected_components: list[DetectedColorRegion],
) -> None:
    print("")
    print("Components:")
    for component in [*accepted_components, *rejected_components]:
        role = component.role
        color = component.color
        bbox = component.bbox
        area = component.area
        reason = component.rejection_reason
        reason_text = "" if reason is None else f" reason={reason}"
        print(f"- role={role} color={color} bbox={bbox} area={area}{reason_text}")


def _clear_generated_outputs(output_dir: Path) -> None:
    for path in output_dir.iterdir():
        if path.is_file() and (
            path.name.endswith("_stage.txt")
            or path.name.endswith("_stage_preview.png")
            or path.name.startswith("manual_reader_")
        ):
            path.unlink()


def _temporary_preview_path() -> Path:
    handle = tempfile.NamedTemporaryFile(
        prefix="manual_reader_",
        suffix=".png",
        dir="/tmp",
        delete=False,
    )
    handle.close()
    return Path(handle.name)


def _output_filename(stage_id: str) -> str:
    if stage_id == "next":
        return "next_stage.txt"
    safe_stage = "".join(
        character if character.isalnum() or character in "-_" else "_" for character in stage_id
    )
    return f"{safe_stage}_stage.txt"


if __name__ == "__main__":
    raise SystemExit(main())
