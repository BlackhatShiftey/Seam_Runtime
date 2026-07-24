# SEAM Public SDK Boundary

The active public integration surface is the Apache-2.0 `seam-client` package
under `sdk/`, published at <https://pypi.org/project/seam-client/>.

## Public

- HTTP transport and bearer authentication
- typed request and response models
- synchronous and asynchronous Python clients
- framework-neutral agent memory hooks
- opaque memory receipts and recall results
- public examples, tests, CI, and release automation

## Private

- MIRL schemas, parsers, compilers, records, and identifiers
- HS/1 and related surface/container codecs
- storage engines and migrations
- retrieval, ranking, graph, compression, reconciliation, and PACK internals
- benchmark holdouts and unpublished measurements
- hosted-service implementation and operator infrastructure

The SDK communicates only through the stable `/v1` agent-memory API:

- `GET /v1/health`
- `POST /v1/memories`
- `POST /v1/memories/recall`
- `POST /v1/context`

The API returns public text and opaque identifiers. It does not return private
record shapes, provenance graphs, ranking traces, packed representations, or
surface payloads.

## Legacy Apache runtime

`seam-runtime` 1.3.0 and 1.3.1 remain historical Apache-2.0 releases. Their
existing grants are not revoked. They are not the source for new private SEAM
runtime development and must not receive private syncs.

New public work belongs in `sdk/`. New private runtime work belongs in the
private SEAM repository.
