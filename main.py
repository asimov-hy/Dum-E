from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    from dume.manual_loop_launcher import main
except ModuleNotFoundError as exc:
    if exc.name not in {"pydantic", "yaml"}:
        raise
    missing_dependency = exc.name

    def main(argv: object = None) -> int:
        print(
            f"Missing project dependency '{missing_dependency}'. "
            "Install the project dependencies, then rerun this command."
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
