# SEAM Public Core Boundary

This document explains how SEAM keeps an independently authored Apache-2.0
client SDK while holding MIRL, HS/1, the private runtime, hosted,
enterprise, customer-specific, and unreleased implementation details under
separate access control.

`LICENSE`, `NOTICE`, and `COMMERCIAL_LICENSE.md` remain the controlling public
license, notice, and commercial-boundary files. This document is an operating
model for repo structure and agent workflow.

## Goals

SEAM should:

- keep the public SDK installable and usable under Apache-2.0;
- preserve the existing Apache grant on the frozen legacy runtime;
- preserve the repo bookkeeping protocol in `AGENTS.md`, `PROJECT_STATUS.md`, `REPO_LEDGER.md`, `HISTORY.md`, `HISTORY_INDEX.md`, and `docs/CODE_LAYOUT.md`;
- avoid adding startup context bloat for future agents;
- make the public-core/private-module boundary obvious to readers and contributors; and
- keep advanced commercial modules, private benchmark holdouts, enterprise connectors, hosted-service code, and unreleased methods outside the public source tree unless intentionally released.

## Public core boundary

The public repository's active distribution and contribution surface is the
Apache-2.0 `seam-client` package under `sdk/`. It may include:

- typed HTTP clients for the opaque public API;
- framework-neutral agent-memory adapters;
- public documentation;
- public client regression tests;
- public adapters and examples;
- public protocol docs; and
- policy files that explain licensing, contribution, security, and commercial
  boundaries.

Apache-2.0 permits use, modification, redistribution, and commercial use of the
public core under the license terms. It does not grant trademark rights or
access to code, services, credentials, data, private repositories, hosted
deployments, enterprise modules, or unreleased methods outside this repository.

The repository also contains the previously released `seam-runtime` 1.x
source. Its Apache-2.0 rights remain intact, but it is a frozen legacy line and
does not receive new proprietary runtime implementation.

## Private/commercial boundary

Private or commercial repositories may hold:

- private benchmark holdouts;
- MIRL and HS/1 implementations, protocols, supporting documentation, and
  related internal methods;
- advanced compression or retrieval experiments before release;
- enterprise-only connectors;
- hosted-service deployment code;
- customer-specific integrations;
- confidential pitch material;
- unreleased architecture notes; and
- any implementation detail that should remain a trade secret or commercial-only module.

Moving future work into a private repository only protects future non-public
code. It does not retract Apache-2.0 rights already granted for public core code
that has been released.

## Independent-development rule

The public SDK is authored and reviewed in this public repository. It is not a
mirror or filtered copy of the private runtime. No private runtime directory,
internal protocol document, generated record, benchmark holdout, or
implementation helper may be copied into `sdk/`.

`sdk/tools/verify_artifact_boundary.py` checks built wheels and source
distributions against an allow-list and rejects private markers. CI must build
from `sdk/` and run that check before publication.

## Agent workflow rule

Do not add this document to the mandatory startup read list unless the task specifically touches licensing, commercial boundaries, contribution policy, repo protection, or public/private separation.

For normal development, agents should continue using the existing startup flow:

1. `PROJECT_STATUS.md`
2. `REPO_LEDGER.md`
3. `HISTORY_INDEX.md`
4. `docs/CODE_LAYOUT.md`
5. targeted `HISTORY.md` entries only when needed

This keeps protection policy visible without forcing future agents to load long legal or policy files during normal runtime work.

## Runtime safety rule

Protection changes must not silently change runtime behavior. A protection-only change should avoid touching:

- `seam_runtime/`
- `seam.py`
- `pyproject.toml`
- installer behavior
- dashboard behavior
- API behavior
- benchmark execution behavior
- history tooling behavior
- active test semantics

If a future protection change needs to alter runtime behavior, it must be handled as an implementation change with tests, history entry, index rebuild, and continuity verification.

## Bookkeeping rule

Protection changes are stable repo policy changes. They should:

- update `REPO_LEDGER.md` with a compact pointer;
- append one `HISTORY.md` entry;
- rebuild `HISTORY_INDEX.md` when local tooling is available;
- write a snapshot when local tooling is available; and
- state skipped verification honestly when changes are made through a connector that cannot run local repo tooling.
