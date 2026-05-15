# Manual Scripts

`read_manual.py` is the current single-page manual_reader utility script.
`run_manual_loop.py` is the manual-only page loop. These scripts are checkout
utilities, not part of the main `dume` CLI.

Basic command:

```bash
python scripts/manuals/read_manual.py --input data/manuals/raw --stage next --mode new-pieces
```

Manual page loop:

```bash
python scripts/manuals/run_manual_loop.py --input data/manuals/raw3
```

To open each generated debug preview while confirming pages:

```bash
python scripts/manuals/run_manual_loop.py \
  --input data/manuals/raw3 \
  --open-preview
```

The script prints to the terminal by default. Use `--output-dir` or
`--preview-output` when a persistent artifact is needed.

Use `--help` to inspect the full argument list when the manual-reader image
dependencies are installed.

See `docs/manuals/manual_reader.md` for usage notes, visual preview options, and
current limitations.
