from __future__ import annotations

import ast
import importlib
import sys
from pathlib import Path

import numpy as np
import pytest

from manuals.formatter import format_manual_stage_result
from manuals.reader import read_manual


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

    result = read_manual(tmp_path, stage_id="next")
    counts = {block.color: block.quantity for block in result.blocks}
    output = format_manual_stage_result(result)

    assert counts["red"] == 2
    assert counts["blue"] == 1
    assert counts["yellow"] == 1
    assert "Stage: next" in output
    assert "Required colored blocks:" in output
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

    result = read_manual(tmp_path, stage_id="next", ignore_colors={"red"})
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
        ignore_hex_colors={"#f2e6c8"},
        hex_tolerance=0,
    )
    counts = {block.color: block.quantity for block in result.blocks}

    assert counts == {"red": 1}
    assert [region.color for region in result.detected_regions] == ["red"]


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
