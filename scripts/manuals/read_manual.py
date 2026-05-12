from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from manuals.color_detector import DEFAULT_THRESHOLDS, detect_color_regions  # noqa: E402
from manuals.formatter import format_manual_stage_result  # noqa: E402
from manuals.reader import ImageLoadError, load_image, read_manual  # noqa: E402
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
        default="data/manuals/extracted",
        help="Directory where extracted text output should be written",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Save and open an annotated visual detection preview",
    )
    parser.add_argument(
        "--preview-output",
        default="data/manuals/extracted/next_stage_preview.png",
        help="Path where the annotated preview image should be written",
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
    return parser


def main() -> int:
    args = build_parser().parse_args()
    ignore_colors = {color.lower() for color in args.ignore_color}
    ignore_hex_colors = set(args.ignore_hex)

    try:
        result = read_manual(
            args.input,
            stage_id=args.stage,
            ignore_colors=ignore_colors,
            ignore_hex_colors=ignore_hex_colors,
            hex_tolerance=args.hex_tolerance,
        )
    except (ImageLoadError, ValueError) as exc:
        print(f"Manual reader error: {exc}")
        return 1

    output = format_manual_stage_result(result)
    print(output)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / _output_filename(args.stage)
    output_path.write_text(output + "\n", encoding="utf-8")

    if args.show:
        preview_path = Path(args.preview_output)
        try:
            _save_and_open_preview(
                result.source_images,
                preview_path,
                ignore_colors,
                ignore_hex_colors,
                args.hex_tolerance,
            )
        except (ImageLoadError, PreviewError, ValueError) as exc:
            print(f"Manual preview error: {exc}")
            return 1

    return 0


def _save_and_open_preview(
    source_images: list[str],
    preview_path: Path,
    ignore_colors: set[str],
    ignore_hex_colors: set[str],
    hex_tolerance: int,
) -> None:
    if not source_images:
        print("No manual image was selected; preview was not generated.")
        return

    image = load_image(source_images[0])
    regions = detect_color_regions(
        image,
        ignore_colors=ignore_colors,
        ignore_hex_colors=ignore_hex_colors,
        hex_tolerance=hex_tolerance,
    )
    ignored_regions = []
    if ignore_colors:
        ignored_thresholds = {
            color: threshold
            for color, threshold in DEFAULT_THRESHOLDS.items()
            if color.lower() in ignore_colors
        }
        if ignored_thresholds:
            ignored_regions = detect_color_regions(image, thresholds=ignored_thresholds)

    saved_path = save_preview(
        image,
        regions,
        preview_path,
        ignored_regions=ignored_regions,
    )
    print(f"Preview saved to: {saved_path}")
    if not open_image(saved_path):
        print(f"Could not open preview automatically. Open manually at: {saved_path}")


def _output_filename(stage_id: str) -> str:
    if stage_id == "next":
        return "next_stage.txt"
    safe_stage = "".join(character if character.isalnum() or character in "-_" else "_" for character in stage_id)
    return f"{safe_stage}_stage.txt"


if __name__ == "__main__":
    raise SystemExit(main())
