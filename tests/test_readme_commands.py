import shlex
from pathlib import Path

from dume.main import build_parser


def _readme_current_commands() -> list[str]:
    readme = Path("README.md").read_text(encoding="utf-8")
    start = readme.index("Current CLI commands:")
    block_start = readme.index("```bash", start) + len("```bash")
    block_end = readme.index("```", block_start)
    return [
        line.strip()
        for line in readme[block_start:block_end].splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def test_readme_current_cli_commands_parse() -> None:
    parser = build_parser()

    for command in _readme_current_commands():
        parts = shlex.split(command)
        assert parts[0] == "dume"
        parser.parse_args(parts[1:])
