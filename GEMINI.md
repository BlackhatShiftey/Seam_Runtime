# GEMINI.md

This model-specific guide is intentionally minimal.
Canonical protocol: `AGENTS.md`.
Current state snapshot: `PROJECT_STATUS.md`.
Historical continuity: `HISTORY_INDEX.md` and surgical reads from `HISTORY.md`.

## SEAM MCP

This repo provides a project-local MCP config at `.gemini/settings.json`.
Gemini should discover the `seam` MCP server automatically when started from
the repo root.

Use SEAM MCP tools when a request depends on repo memory, durable history,
roadmap state, prior decisions, stored documents, HS/1 surfaces, or benchmark
evidence. Prefer `seam_context` for prompt-ready context, `seam_memory_search`
then `seam_memory_get` for progressive detail, and `seam_retrieve` with
`mode=mix` for RAG-style lookup. Use `seam_ingest` only when the user asks to
store durable memory.
