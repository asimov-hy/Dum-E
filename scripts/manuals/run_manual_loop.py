from __future__ import annotations

import argparse
import re
import shutil
import sys
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from manuals.formatter import format_manual_stage_result  # noqa: E402
from manuals.reader import IMAGE_EXTENSIONS, ImageLoadError, read_manual  # noqa: E402
from manuals.types import ManualStageResult, ReaderMode  # noqa: E402
from manuals.visual_debug import PreviewError, open_image  # noqa: E402
from scripts.manuals.read_manual import (  # noqa: E402
    _print_debug_components,
    _save_and_open_preview,
)

LoopAction = str
WaitFunc = Callable[[str], LoopAction]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run manual pages one at a time")
    parser.add_argument(
        "--input",
        default="data/manuals/raw",
        help="Directory containing manual image files",
    )
    parser.add_argument(
        "--mode",
        choices=("new-pieces", "visible-blocks"),
        default="new-pieces",
        help="Reader mode for each page.",
    )
    parser.add_argument(
        "--preview-dir",
        default=None,
        help="Optional directory for per-page debug previews.",
    )
    parser.add_argument(
        "--debug-components",
        action="store_true",
        help="Print classified component boxes, roles, and rejection reasons.",
    )
    parser.add_argument(
        "--open-image",
        action="store_true",
        help="Open the current source image with the system image viewer when possible.",
    )
    parser.add_argument(
        "--stop-after",
        type=int,
        default=None,
        help="Stop after N pages.",
    )
    parser.add_argument(
        "--repeat-on-fail",
        action="store_true",
        help="Stay on the current page when the reader returns a non-ok status.",
    )
    parser.add_argument(
        "--wait-mode",
        choices=("enter",),
        default="enter",
        help="Wait strategy. Current manual-only mode advances on Enter.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.stop_after is not None and args.stop_after < 1:
        print("Manual loop error: --stop-after must be positive")
        return 1

    return run_loop(
        Path(args.input),
        mode=args.mode,
        preview_dir=Path(args.preview_dir) if args.preview_dir else None,
        debug_components=args.debug_components,
        open_image_flag=args.open_image,
        stop_after=args.stop_after,
        repeat_on_fail=args.repeat_on_fail,
        wait_mode=args.wait_mode,
    )


def iter_manual_pages(input_dir: Path) -> list[Path]:
    directory = Path(input_dir)
    if not directory.exists():
        raise FileNotFoundError(f"Input directory does not exist: {directory}")
    if not directory.is_dir():
        raise NotADirectoryError(f"Input path is not a directory: {directory}")

    pages = [
        path
        for path in directory.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    ]
    return sorted(pages, key=_page_sort_key)


def wait_for_confirmation(wait_mode: str = "enter") -> LoopAction:
    if wait_mode != "enter":
        raise ValueError(f"Unsupported wait mode: {wait_mode}")
    try:
        response = input("Press Enter for next page, r to repeat, q to quit: ")
    except EOFError:
        return "quit"

    normalized = response.strip().lower()
    if normalized == "q":
        return "quit"
    if normalized == "r":
        return "repeat"
    return "advance"


def process_page(
    page: Path,
    *,
    input_dir: Path,
    mode: ReaderMode,
    preview_dir: Path | None = None,
    debug_components: bool = False,
    open_image_flag: bool = False,
) -> ManualStageResult:
    with tempfile.TemporaryDirectory(prefix="manual_loop_") as temporary_directory:
        page_copy = Path(temporary_directory) / page.name
        shutil.copy2(page, page_copy)
        result = replace(
            read_manual(Path(temporary_directory), stage_id="next", mode=mode),
            source_images=[str(page)],
            page_filename=page.name,
        )
        print(format_manual_stage_result(result))

        if debug_components:
            _print_debug_components(result.accepted_components, result.rejected_components)

        if preview_dir is not None:
            preview_path = preview_dir / f"{page.stem}_preview.png"
            _save_and_open_preview(
                result.source_images,
                preview_path,
                mode,
                set(),
                set(),
                25,
                [],
                [],
                100,
                None,
                False,
                False,
                open_preview=False,
            )

    if open_image_flag and not open_image(page):
        print(f"Could not open image automatically. Open manually at: {page}")

    return result


def run_loop(
    input_dir: Path,
    *,
    mode: ReaderMode = "new-pieces",
    preview_dir: Path | None = None,
    debug_components: bool = False,
    open_image_flag: bool = False,
    stop_after: int | None = None,
    repeat_on_fail: bool = False,
    wait_mode: str = "enter",
    wait_func: WaitFunc = wait_for_confirmation,
) -> int:
    try:
        pages = iter_manual_pages(input_dir)
    except (FileNotFoundError, NotADirectoryError) as exc:
        print(f"Manual loop error: {exc}")
        return 1

    if not pages:
        print(f"Manual loop error: no manual images found in {input_dir}")
        return 1

    if stop_after is not None:
        pages = pages[:stop_after]

    page_index = 0
    while page_index < len(pages):
        page = pages[page_index]
        print("")
        print(f"===== Page {page_index + 1}/{len(pages)}: {page.name} =====")

        try:
            result = process_page(
                page,
                input_dir=input_dir,
                mode=mode,
                preview_dir=preview_dir,
                debug_components=debug_components,
                open_image_flag=open_image_flag,
            )
        except (ImageLoadError, PreviewError, ValueError) as exc:
            print(f"Manual loop error while reading {page.name}: {exc}")
            if not repeat_on_fail:
                return 1
            result = None

        action = wait_func(wait_mode)
        if action == "quit":
            print("Manual loop quit.")
            return 0
        if action == "repeat":
            continue
        if action != "advance":
            print(f"Manual loop error: unsupported wait action: {action}")
            return 1
        if repeat_on_fail and result is not None and _page_failed(result):
            print("Repeat-on-fail is enabled; staying on current page.")
            continue

        page_index += 1

    print("")
    print("Manual loop complete.")
    return 0


def _page_failed(result: ManualStageResult) -> bool:
    return result.status not in {"ok", "ok_no_arrow_detected"}


def _page_sort_key(path: Path) -> tuple[bool, int, tuple[tuple[int, int | str], ...]]:
    stage_number = _stage_number(path.stem)
    return (
        stage_number is None,
        stage_number or 0,
        _natural_key(path.name),
    )


def _stage_number(stem: str) -> int | None:
    match = re.search(r"(?:^|[^a-z0-9])c(\d+)(?=$|[^a-z0-9])", stem.lower())
    if match is None:
        return None
    return int(match.group(1))


def _natural_key(value: str) -> tuple[tuple[int, int | str], ...]:
    parts = re.split(r"(\d+)", value)
    return tuple(
        (0, int(part)) if part.isdigit() else (1, part.lower())
        for part in parts
    )


if __name__ == "__main__":
    raise SystemExit(main())
