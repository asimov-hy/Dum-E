from __future__ import annotations

import ast
import importlib
import sys
from pathlib import Path

import numpy as np
import pytest

from manuals.color_detector import parse_region
from manuals.formatter import format_manual_stage_result
from manuals.reader import read_manual
from manuals.types import ManualStageResult
from manuals.visual_debug import has_preview_backend
from scripts.manuals import read_manual as cli
from scripts.manuals import run_manual_loop as loop_cli


ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_MANUAL_IMPORTS = {
    "dume.control",
    "dume.integrations.lerobot",
    "mediapipe",
    "lerobot",
}


def test_reader_aggregates_repeated_colors_and_formats_text(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image_path = tmp_path / "next-stage.png"
    image_path.write_bytes(b"synthetic placeholder")

    image = np.full((80, 140, 3), (0, 255, 255), dtype=np.uint8)
    image[10:30, 10:30] = (255, 0, 0)
    image[10:30, 40:60] = (255, 0, 0)
    image[10:30, 70:90] = (0, 0, 255)
    image[40:60, 10:30] = (255, 255, 0)

    monkeypatch.setattr("manuals.reader.load_image", lambda path: image)

    result = read_manual(tmp_path, stage_id="next", mode="visible-blocks")
    counts = {block.color: block.quantity for block in result.blocks}
    output = format_manual_stage_result(result)

    assert counts["red"] == 2
    assert counts["blue"] == 1
    assert counts["yellow"] == 1
    assert "Stage: next" in output
    assert "Required active colors:" in output
    assert "- red" in output
    assert "Component counts:" in output
    assert "- red: 2" in output


def test_reader_ignore_color_removes_color_from_result_and_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image_path = tmp_path / "next-stage.png"
    image_path.write_bytes(b"synthetic placeholder")

    image = np.full((80, 120, 3), (0, 255, 255), dtype=np.uint8)
    image[10:30, 10:30] = (255, 0, 0)
    image[10:30, 40:60] = (0, 0, 255)

    monkeypatch.setattr("manuals.reader.load_image", lambda path: image)

    result = read_manual(tmp_path, stage_id="next", mode="visible-blocks", ignore_colors={"red"})
    counts = {block.color: block.quantity for block in result.blocks}
    output = format_manual_stage_result(result)

    assert "red" not in counts
    assert counts["blue"] == 1
    assert "- red:" not in output
    assert "- blue: 1" in output


def test_reader_ignore_hex_removes_manual_background_color(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image_path = tmp_path / "next-stage.png"
    image_path.write_bytes(b"synthetic placeholder")

    image = np.full((80, 120, 3), (242, 230, 200), dtype=np.uint8)
    image[10:30, 10:30] = (255, 0, 0)

    monkeypatch.setattr("manuals.reader.load_image", lambda path: image)

    result = read_manual(
        tmp_path,
        stage_id="next",
        mode="visible-blocks",
        ignore_hex_colors={"#f2e6c8"},
        hex_tolerance=0,
    )
    counts = {block.color: block.quantity for block in result.blocks}

    assert counts == {"red": 1}
    assert [region.color for region in result.detected_regions] == ["red"]


def test_reader_applies_spatial_regions_before_counting(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image_path = tmp_path / "next-stage.png"
    image_path.write_bytes(b"synthetic placeholder")

    image = np.full((80, 120, 3), (0, 255, 255), dtype=np.uint8)
    image[10:30, 10:30] = (255, 0, 0)
    image[10:30, 60:80] = (0, 0, 255)

    monkeypatch.setattr("manuals.reader.load_image", lambda path: image)

    result = read_manual(
        tmp_path,
        stage_id="next",
        mode="visible-blocks",
        include_regions=[parse_region("0,0,100,80")],
        exclude_regions=[parse_region("5,5,35,35")],
    )
    counts = {block.color: block.quantity for block in result.blocks}

    assert counts == {"blue": 1}
    assert [region.color for region in result.detected_regions] == ["blue"]


def test_reader_default_new_pieces_accepts_active_block_without_arrow(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image_path = tmp_path / "next-stage.png"
    image_path.write_bytes(b"synthetic placeholder")

    image = np.full((80, 120, 3), (255, 255, 255), dtype=np.uint8)
    image[10:30, 10:30] = (0, 128, 0)

    monkeypatch.setattr("manuals.reader.load_image", lambda path: image)

    result = read_manual(tmp_path, stage_id="next")
    counts = {block.color: block.quantity for block in result.blocks}

    assert counts == {"green": 1}
    assert result.mode == "new-pieces"
    assert result.status == "ok_no_arrow_detected"
    assert "no arrows detected" in result.warnings


def test_c1_like_page_returns_active_green_components_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image_path = tmp_path / "manual2-c1.png"
    image_path.write_bytes(b"synthetic placeholder")

    image = _c1_like_image()
    monkeypatch.setattr("manuals.reader.load_image", lambda path: image)

    result = read_manual(tmp_path, stage_id="next", min_region_area=20)
    counts = {block.color: block.quantity for block in result.blocks}
    rejected_roles = {component.role for component in result.rejected_components}

    assert counts == {"green": 2}
    assert result.active_colors == ["green"]
    assert {component.role for component in result.accepted_components} == {"ACTIVE_BLOCK"}
    assert {"ARROW", "TEXT", "BACKGROUND"}.issubset(rejected_roles)


def test_raw3_pages_report_expected_active_color_sets() -> None:
    pytest.importorskip("PIL.Image")
    input_dir = ROOT / "data" / "manuals" / "raw3"
    if not input_dir.exists():
        pytest.skip("raw3 manual fixtures are not available")

    expected_colors = {
        "c1": {"green"},
        "c2": {"green"},
        "c3": {"green", "white"},
        "c4": {"green", "white", "yellow"},
        "c5": {"green", "white", "yellow"},
    }

    for stage_id, colors in expected_colors.items():
        result = read_manual(input_dir, stage_id=stage_id)
        assert set(result.active_colors) == colors


def test_manual_loop_orders_pages_by_stage_number_then_natural_name(tmp_path: Path) -> None:
    for name in (
        "manual2-c10.png",
        "cover.png",
        "manual2-c2.png",
        "manual2-c1.png",
        "manual2-c5.jpg",
    ):
        (tmp_path / name).write_bytes(b"synthetic placeholder")

    pages = loop_cli.iter_manual_pages(tmp_path)

    assert [page.name for page in pages] == [
        "manual2-c1.png",
        "manual2-c2.png",
        "manual2-c5.jpg",
        "manual2-c10.png",
        "cover.png",
    ]


def test_manual_loop_repeats_advances_and_quits(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in ("manual2-c1.png", "manual2-c2.png", "manual2-c3.png"):
        (tmp_path / name).write_bytes(b"synthetic placeholder")

    processed_pages: list[str] = []
    actions = iter(("repeat", "advance", "quit"))

    def fake_process_page(page: Path, **kwargs: object) -> ManualStageResult:
        processed_pages.append(page.name)
        return ManualStageResult(stage_id=page.stem, active_colors=["green"])

    monkeypatch.setattr(loop_cli, "process_page", fake_process_page)

    result = loop_cli.run_loop(
        tmp_path,
        wait_func=lambda wait_mode: next(actions),
    )

    assert result == 0
    assert processed_pages == ["manual2-c1.png", "manual2-c1.png", "manual2-c2.png"]


def test_cli_default_run_does_not_create_output_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    input_dir = _manual_input_dir(tmp_path)
    monkeypatch.setattr("manuals.reader.load_image", lambda path: _c1_like_image())
    monkeypatch.setattr(sys, "argv", ["read_manual.py", "--input", str(input_dir)])

    assert cli.main() == 0
    assert not (tmp_path / "extracted").exists()
    assert not (input_dir / "next_stage.txt").exists()


def test_cli_preview_output_writes_only_explicit_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if not has_preview_backend():
        pytest.skip("OpenCV or Pillow is required for preview generation")

    input_dir = _manual_input_dir(tmp_path)
    preview_path = tmp_path / "debug" / "manual.png"
    image = _c1_like_image()
    monkeypatch.setattr("manuals.reader.load_image", lambda path: image)
    monkeypatch.setattr("scripts.manuals.read_manual.load_image", lambda path: image)
    monkeypatch.setattr(
        sys,
        "argv",
        ["read_manual.py", "--input", str(input_dir), "--preview-output", str(preview_path)],
    )

    assert cli.main() == 0
    assert preview_path.exists()
    assert not (tmp_path / "data").exists()


def test_cli_output_dir_writes_only_when_provided(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    input_dir = _manual_input_dir(tmp_path)
    output_dir = tmp_path / "out"
    monkeypatch.setattr("manuals.reader.load_image", lambda path: _c1_like_image())
    monkeypatch.setattr(
        sys,
        "argv",
        ["read_manual.py", "--input", str(input_dir), "--output-dir", str(output_dir)],
    )

    assert cli.main() == 0
    assert (output_dir / "next_stage.txt").exists()
    assert not (tmp_path / "data").exists()


def test_cli_clear_output_dir_clears_generated_files_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    input_dir = _manual_input_dir(tmp_path)
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    (output_dir / "old_stage.txt").write_text("old", encoding="utf-8")
    (output_dir / "keep.txt").write_text("keep", encoding="utf-8")

    monkeypatch.setattr("manuals.reader.load_image", lambda path: _c1_like_image())
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "read_manual.py",
            "--input",
            str(input_dir),
            "--output-dir",
            str(output_dir),
            "--clear-output-dir",
        ],
    )

    assert cli.main() == 0
    assert not (output_dir / "old_stage.txt").exists()
    assert (output_dir / "keep.txt").exists()
    assert (output_dir / "next_stage.txt").exists()


def test_reader_handles_empty_input_directory_cleanly(tmp_path: Path) -> None:
    result = read_manual(tmp_path, stage_id="next")
    output = format_manual_stage_result(result)

    assert result.blocks == []
    assert result.source_images == []
    assert result.notes == [f"No manual images found in {tmp_path}"]
    assert "- none detected" in output


def test_manuals_do_not_import_robot_control_mediapipe_or_lerobot() -> None:
    forbidden_loaded_roots = {"mediapipe", "lerobot"}
    forbidden_loaded_modules = {
        "dume.control",
        "dume.integrations.lerobot",
    }
    for module_name in list(sys.modules):
        if (
            module_name == "manuals"
            or module_name.startswith("manuals.")
            or module_name in forbidden_loaded_modules
            or any(module_name.startswith(f"{name}.") for name in forbidden_loaded_modules)
            or module_name.split(".", 1)[0] in forbidden_loaded_roots
        ):
            del sys.modules[module_name]

    importlib.import_module("manuals")

    loaded_roots = {module_name.split(".", 1)[0] for module_name in sys.modules}
    assert loaded_roots.isdisjoint(forbidden_loaded_roots)
    assert "dume.control" not in sys.modules
    assert "dume.integrations.lerobot" not in sys.modules

    violations = []
    for path in (ROOT / "manuals").rglob("*.py"):
        imported_modules = _imported_modules(path)
        illegal_imports = {
            imported
            for imported in imported_modules
            if any(
                imported == forbidden or imported.startswith(f"{forbidden}.")
                for forbidden in FORBIDDEN_MANUAL_IMPORTS
            )
        }
        if illegal_imports:
            violations.append(
                f"{path.relative_to(ROOT)} imports forbidden module(s): "
                f"{', '.join(sorted(illegal_imports))}"
            )

    assert violations == []


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

    return imports


def _manual_input_dir(tmp_path: Path) -> Path:
    input_dir = tmp_path / "raw"
    input_dir.mkdir()
    (input_dir / "manual2-c1.png").write_bytes(b"synthetic placeholder")
    return input_dir


def _c1_like_image() -> np.ndarray:
    image = np.full((140, 180, 3), (255, 255, 255), dtype=np.uint8)
    image[8:45, 12:18] = (0, 0, 0)
    image[8:14, 12:38] = (0, 0, 0)
    image[39:45, 12:38] = (0, 0, 0)
    image[8:45, 55:61] = (0, 0, 0)
    image[84:90, 48:68] = (0, 0, 0)
    image[55:82, 32:82] = (0, 165, 0)
    image[94:122, 38:88] = (0, 165, 0)
    image[64:105, 112:116] = (0, 0, 255)
    image[101:110, 107:121] = (0, 0, 255)
    return image
