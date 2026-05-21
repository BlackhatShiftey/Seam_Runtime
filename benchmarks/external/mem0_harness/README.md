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

## Known comparator gaps

mem0ai's internal client sends `max_tokens` to OpenAI completion endpoints.
GPT-5 and o-series models reject `max_tokens` and require
`max_completion_tokens`. To run the mem0 comparator today, pin the mem0
client model to a chat-completion model that still accepts `max_tokens`:

```bash
export MEM0_LLM_MODEL=gpt-4o-mini
```

When `MEM0_LLM_MODEL` is unset or names a gpt-5/o-series model, the mem0
comparator will fail; report the failure verbatim and skip the comparator
column rather than fabricating a mem0 score.

If mem0ai's later release accepts the modern parameter, remove this note in
the same commit that bumps the pin.
