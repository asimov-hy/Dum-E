import ast
import importlib
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ("core", "camera", "perception")


def _clear_media_pipeline_modules() -> None:
    for module_name in list(sys.modules):
        if module_name in PACKAGES or module_name.startswith(tuple(f"{pkg}." for pkg in PACKAGES)):
            del sys.modules[module_name]


def _assert_import_does_not_load(module_name: str, forbidden: set[str]) -> None:
    _clear_media_pipeline_modules()

    importlib.import_module(module_name)

    loaded_roots = {name.split(".", 1)[0] for name in sys.modules}
    assert loaded_roots.isdisjoint(forbidden)


def test_core_imports_do_not_load_camera_or_perception() -> None:
    for module_name in ("core", "core.frame", "core.landmarks", "core.types"):
        _assert_import_does_not_load(module_name, {"camera", "perception"})


def test_camera_import_does_not_load_perception() -> None:
    _assert_import_does_not_load("camera", {"perception"})


def test_perception_imports_do_not_load_camera() -> None:
    for module_name in ("perception", "perception.types"):
        _assert_import_does_not_load(module_name, {"camera"})


def _top_level_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".", 1)[0])

    return imports


def test_source_import_boundaries_are_static() -> None:
    rules = {
        "core": {"camera", "perception"},
        "camera": {"perception"},
        "perception": {"camera"},
    }
    violations = []

    for package_name, forbidden_imports in rules.items():
        for path in (ROOT / package_name).rglob("*.py"):
            illegal_imports = _top_level_imports(path) & forbidden_imports
            if illegal_imports:
                violations.append(
                    f"{path.relative_to(ROOT)} imports forbidden package(s): "
                    f"{', '.join(sorted(illegal_imports))}"
                )

    assert violations == []
