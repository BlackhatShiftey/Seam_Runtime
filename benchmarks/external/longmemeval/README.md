# LongMemEval benchmark runner

Evaluates long-context memory retrieval with 500 questions across 5 categories:
information extraction, multi-session reasoning, temporal reasoning, knowledge
updates, and abstention.

## Quickstart

```bash
# Validate a local dataset without executing:
.venv/bin/python -m benchmarks.external.longmemeval.run \
    --dataset-path /path/to/longmemeval.json --dry-run
```

## Dataset

The LongMemEval dataset is not bundled. Download it from the public LongMemEval
release and point `--dataset-path` at the JSON file.

Expected shape: 500 total questions, 5 categories:
`information_extraction`, `multi_session_reasoning`, `temporal_reasoning`,
`knowledge_updates`, `abstention`.

## Dry-run validation

Dry-run prints case counts, category breakdown, fixture hash, and validation
issues without executing the judge or adapter. Use it to verify dataset
integrity before committing to a real run.
