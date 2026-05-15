"""SEAM Context Streams substrate (Track H1).

The single-stream HISTORY.md + HISTORY_INDEX.md pattern is generalized into a
multi-stream protocol so each growing dimension (history, roadmap, experience,
library, improvement) gets its own append-only log + derived index without
collapsing under its own weight.

Phase 1 (this package): the substrate. Root HISTORY.md / HISTORY_INDEX.md
remain canonical; .seam/streams/history/* are byte-equivalent derived mirrors
via a compatibility adapter. New roadmap + experience streams live entirely
under .seam/streams/. A derived (not append-only canonical) .seam/cross_index.md
provides the global temporal join.

See docs/roadmap/CONTEXT_STREAMS.md for the full design.
"""
