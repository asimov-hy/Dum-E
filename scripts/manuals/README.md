# Manual Scripts

`read_manual.py` is the current manual_reader utility script. These scripts are
checkout utilities, not part of the main `dume` CLI.

Basic command:

```bash
python scripts/manuals/read_manual.py --input data/manuals/raw --stage next --mode new-pieces
```

The script prints to the terminal by default. Use `--output-dir` or
`--preview-output` when a persistent artifact is needed.

Use `--help` to inspect the full argument list when the manual-reader image
dependencies are installed.

See `docs/manuals/manual_reader.md` for usage notes, visual preview options, and
current limitations.
