# BEAM benchmark runner

Evaluates memory over long conversations with probing questions.

## Tracks

- **BEAM-1M**: 100 conversations, 2,000 probing questions (supported)
- **BEAM-10M**: large-scale track (explicitly deferred; refused by the runner)

## Quickstart

```bash
# Validate a local dataset directory without executing:
.venv/bin/python -m benchmarks.external.beam.run \
    --track 1m --dataset-path /path/to/beam-dataset-dir --dry-run
```

## Dataset

The BEAM dataset is not bundled. Download it from the public BEAM release
and point `--dataset-path` at the dataset directory.

BEAM-1M expected shape: 100 conversation subdirectories, ~2,000 total probing questions.

## Dry-run validation

Dry-run scans the dataset directory, counts conversations and questions, and
reports validation issues without executing the judge or adapter.
