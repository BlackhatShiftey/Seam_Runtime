# SEAM mem0 harness adapter

Thin adapter that wires SEAM into the open-source
[mem0ai/memory-benchmarks](https://github.com/mem0ai/memory-benchmarks)
harness so numbers are comparable to the public ecosystem.

## Protocol

The adapter exposes `add(messages, user_id)`, `search(query, user_id, limit)`,
and `delete(user_id)`, matching the harness interface. Each `user_id` maps to
a per-conversation SQLite database; SEAM's runtime handles ingest, MIRL
compilation, and retrieval internally.

## Contract tests

```
.venv/bin/python -m pytest tests/audit/test_mem0_harness_adapter_contract.py -v
```

Tests use an in-repo tiny fixture and require no network, API keys, or the
upstream harness clone.

## Manual run against a local harness clone

```bash
git clone https://github.com/mem0ai/memory-benchmarks ../memory-benchmarks
.venv/bin/python -m benchmarks.external.mem0_harness.adapter \
    --harness ../memory-benchmarks --dataset locomo --dry-run
```

Record the upstream commit used in any result claim:
```bash
git -C ../memory-benchmarks rev-parse HEAD
```
