from __future__ import annotations

import argparse
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
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
        "--open-preview",
        action="store_true",
        help="Generate and open each per-page debug preview while waiting for confirmation.",
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
        choices=("enter", "gesture"),
        default="enter",
        help="Wait strategy. Enter mode advances on keyboard input; gesture mode uses MediaPipe.",
    )
    parser.add_argument(
        "--gesture-source",
        choices=("webcam", "realsense", "fake", "video"),
        default="webcam",
        help="Frame source for --wait-mode gesture.",
    )
    parser.add_argument(
        "--gesture-video-path",
        default=None,
        help="Video file path when --gesture-source video is used.",
    )
    parser.add_argument(
        "--gesture-model-path",
        default="data/mediapipe/models/gesture_recognizer.task",
        help="MediaPipe gesture recognizer .task model path.",
    )
    parser.add_argument(
        "--gesture-timeout-s",
        type=float,
        default=None,
        help="Optional gesture wait timeout. Timeout quits unless --gesture-fallback enter is set.",
    )
    parser.add_argument(
        "--gesture-fallback",
        choices=("enter",),
        default=None,
        help="Fallback to keyboard input if gesture startup or timeout cannot produce an action.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.stop_after is not None and args.stop_after < 1:
        print("Manual loop error: --stop-after must be positive")
        return 1
    if args.gesture_timeout_s is not None and args.gesture_timeout_s < 0:
        print("Manual loop error: --gesture-timeout-s must not be negative")
        return 1

    wait_mode = args.wait_mode
    wait_func: WaitFunc = wait_for_confirmation
    gesture_wait = None

    if args.wait_mode == "gesture":
        try:
            from scripts.manuals.gesture_wait import build_gesture_wait

            gesture_wait = build_gesture_wait(
                source_name=args.gesture_source,
                video_path=args.gesture_video_path,
                model_path=args.gesture_model_path,
                timeout_s=args.gesture_timeout_s,
                fallback_wait_func=wait_for_confirmation
                if args.gesture_fallback == "enter"
                else None,
            )
            gesture_wait.start()
            wait_func = gesture_wait
        except Exception as exc:
            if args.gesture_fallback == "enter":
                print(f"Gesture wait unavailable ({exc}); falling back to keyboard input.")
                wait_mode = "enter"
                wait_func = wait_for_confirmation
                if gesture_wait is not None:
                    gesture_wait.close()
                    gesture_wait = None
            else:
                print(f"Manual loop error: could not start gesture wait: {exc}")
                if gesture_wait is not None:
                    gesture_wait.close()
                return 1

    try:
        return run_loop(
            Path(args.input),
            mode=args.mode,
            preview_dir=Path(args.preview_dir) if args.preview_dir else None,
            open_preview_flag=args.open_preview,
            debug_components=args.debug_components,
            open_image_flag=args.open_image,
            stop_after=args.stop_after,
            repeat_on_fail=args.repeat_on_fail,
            wait_mode=wait_mode,
            wait_func=wait_func,
        )
    finally:
        if gesture_wait is not None:
            gesture_wait.close()


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


def open_preview(path: Path) -> subprocess.Popen | None:
    """Open a preview with a viewer process the loop can later terminate."""
    if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        return None

    for command in _managed_preview_commands(path):
        popen_kwargs: dict[str, object] = {
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
        }
        if os.name == "posix":
            popen_kwargs["start_new_session"] = True
        try:
            process = subprocess.Popen(command, **popen_kwargs)
        except OSError:
            continue

        time.sleep(0.15)
        if process.poll() is None:
            return process
        process.wait()

    return None


def close_preview(proc: subprocess.Popen | None) -> None:
    if proc is None:
        return

    _terminate_preview_process(proc, signal.SIGTERM)

    try:
        proc.wait(timeout=2.0)
    except subprocess.TimeoutExpired:
        _terminate_preview_process(proc, signal.SIGKILL)
        proc.wait(timeout=2.0)


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
    open_preview_flag: bool = False,
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
    preview_process: subprocess.Popen | None = None
    preview_page_index: int | None = None
    temporary_preview_dir: tempfile.TemporaryDirectory[str] | None = None
    effective_preview_dir = preview_dir
    if open_preview_flag and effective_preview_dir is None:
        temporary_preview_dir = tempfile.TemporaryDirectory(prefix="dume_manual_loop_previews_")
        effective_preview_dir = Path(temporary_preview_dir.name)

    try:
        while page_index < len(pages):
            page = pages[page_index]
            print("")
            print(f"===== Page {page_index + 1}/{len(pages)}: {page.name} =====")

            try:
                result = process_page(
                    page,
                    input_dir=input_dir,
                    mode=mode,
                    preview_dir=effective_preview_dir,
                    debug_components=debug_components,
                    open_image_flag=open_image_flag,
                )
            except (ImageLoadError, PreviewError, ValueError) as exc:
                print(f"Manual loop error while reading {page.name}: {exc}")
                if not repeat_on_fail:
                    return 1
                result = None

            if result is not None and open_preview_flag and preview_page_index != page_index:
                preview_path = _preview_path(effective_preview_dir, page)
                preview_process = open_preview(preview_path)
                preview_page_index = page_index
                if preview_process is None:
                    print(f"Could not open preview automatically. Open manually at: {preview_path}")

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

            close_preview(preview_process)
            preview_process = None
            preview_page_index = None
            page_index += 1
    finally:
        close_preview(preview_process)
        if temporary_preview_dir is not None:
            temporary_preview_dir.cleanup()

    print("")
    print("Manual loop complete.")
    return 0


def _page_failed(result: ManualStageResult) -> bool:
    return result.status not in {"ok", "ok_no_arrow_detected"}


def _preview_path(preview_dir: Path | None, page: Path) -> Path:
    if preview_dir is None:
        raise ValueError("Preview directory is required when opening loop previews.")
    return preview_dir / f"{page.stem}_preview.png"


def _terminate_preview_process(proc: subprocess.Popen, sig: signal.Signals) -> None:
    if os.name == "posix":
        try:
            os.killpg(proc.pid, sig)
            return
        except ProcessLookupError:
            pass
        except OSError:
            pass

    if proc.poll() is None:
        if sig == signal.SIGTERM:
            proc.terminate()
        else:
            proc.kill()


def _managed_preview_commands(path: Path) -> list[list[str]]:
    commands: list[list[str]] = []
    # xdg-open/gio normally hand off to another process and exit, so this loop
    # uses direct viewers whose process can be terminated before the next page.
    viewer_specs = (
        ("eog", ["--new-instance"]),
        ("xviewer", ["--new-instance"]),
        ("feh", ["--auto-zoom", "--scale-down"]),
        ("imv", []),
        ("nsxiv", []),
        ("sxiv", []),
        ("ristretto", []),
        ("gpicview", []),
        ("display", []),
    )
    for executable, args in viewer_specs:
        resolved = shutil.which(executable)
        if resolved is not None:
            commands.append([resolved, *args, str(path)])
    return commands


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
