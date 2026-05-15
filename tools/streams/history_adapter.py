"""History stream compatibility adapter.

Phase 1 rule: root HISTORY.md / HISTORY_INDEX.md remain canonical. The history
stream is surfaced by mirroring those root files into
.seam/streams/history/log.md and .seam/streams/history/index.md as
byte-equivalent derived artifacts. Generic stream tooling can read the mirror
just like any other stream's log; consumers that have not been migrated still
read the root files.

Path canonicality flip from root to .seam/streams/history/ is explicitly
deferred to a separate later HISTORY entry per CONTEXT_STREAMS.md §9.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from tools.history.history_lib import HISTORY_PATH, INDEX_PATH
from tools.streams.streams_lib import STREAMS_ROOT


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sync_history_mirror() -> dict[str, object]:
    """Regenerate .seam/streams/history/{log,index}.md as byte-equivalent mirrors.

    Returns a dict with the source/mirror paths, content sha256, and whether
    any change was written. Safe to run repeatedly; only writes when bytes
    actually differ to avoid mtime churn.
    """
    mirror_dir = STREAMS_ROOT / "history"
    mirror_dir.mkdir(parents=True, exist_ok=True)
    log_dest = mirror_dir / "log.md"
    index_dest = mirror_dir / "index.md"

    log_changed = _mirror_file(HISTORY_PATH, log_dest)
    index_changed = _mirror_file(INDEX_PATH, index_dest)

    return {
        "kind": "history",
        "source_log": str(HISTORY_PATH),
        "mirror_log": str(log_dest),
        "source_index": str(INDEX_PATH),
        "mirror_index": str(index_dest),
        "log_sha256": _sha256(HISTORY_PATH.read_bytes()) if HISTORY_PATH.exists() else None,
        "index_sha256": _sha256(INDEX_PATH.read_bytes()) if INDEX_PATH.exists() else None,
        "log_changed": log_changed,
        "index_changed": index_changed,
    }


def _mirror_file(src: Path, dest: Path) -> bool:
    if not src.exists():
        if dest.exists():
            dest.unlink()
            return True
        return False
    src_bytes = src.read_bytes()
    if dest.exists() and dest.read_bytes() == src_bytes:
        return False
    dest.write_bytes(src_bytes)
    return True


def verify_history_mirror() -> list[str]:
    """Return a list of issue strings; empty means the mirror matches root."""
    issues: list[str] = []
    log_dest = STREAMS_ROOT / "history" / "log.md"
    index_dest = STREAMS_ROOT / "history" / "index.md"
    if HISTORY_PATH.exists():
        if not log_dest.exists():
            issues.append("history mirror log missing; run `python -m tools.streams.history_adapter`")
        elif log_dest.read_bytes() != HISTORY_PATH.read_bytes():
            issues.append("history mirror log diverges from HISTORY.md; rerun mirror")
    if INDEX_PATH.exists():
        if not index_dest.exists():
            issues.append("history mirror index missing; run `python -m tools.streams.history_adapter`")
        elif index_dest.read_bytes() != INDEX_PATH.read_bytes():
            issues.append("history mirror index diverges from HISTORY_INDEX.md; rerun mirror")
    return issues


def main() -> int:
    result = sync_history_mirror()
    print(
        f"history mirror: log_changed={result['log_changed']} index_changed={result['index_changed']} "
        f"log_sha256={result['log_sha256']} index_sha256={result['index_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
