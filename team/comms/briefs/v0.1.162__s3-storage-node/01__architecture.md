# S3 Storage Node — Architecture

**version** v0.1.162
**date** 2026-05-04
**from** Developer Agent (Node Specs session)
**to** Architect, Dev
**type** Architecture reference

---

## 1. The Two-Layer Split

The S3 Storage Node splits across two Python packages:

```
sg_compute_specs/s3_server/   ← Node Spec (thin launch + connect shell)
sg_s3_server/                 ← S3 server implementation (HTTP, call log, backends)
```

`sg_compute_specs/s3_server/` follows the exact docker spec pattern.  Its job
is to describe how to launch, connect to, and tear down an S3 server node.  It
does NOT contain HTTP parsing, SigV4 logic, or bucket management — those live
in `sg_s3_server/`.

This split keeps the spec thin (same scope as docker/ollama/opensearch specs)
while letting the server evolve independently without touching the spec layer.

---

## 2. What a Node Spec Is (recap)

A spec in `sg_compute_specs/` is:

1. `manifest.py` — typed `Schema__Spec__Manifest__Entry` consumed by
   `Spec__Loader`.
2. Enums / primitives / schemas / collections — the typed surface for
   create/list/info/delete/health operations on nodes of this type.
3. Service helpers — AWS helpers (SG, AMI, tags, launch, mapper),
   user-data builder, health checker, orchestrator (`S3_Server__Service`).
4. FastAPI routes — thin delegation under `/api/specs/s3_server/stack*`.
5. Tests — unit tests for all of the above; no mocks, no AWS calls.

The docker spec (`sg_compute_specs/docker/`) is the canonical template.

---

## 3. New Enum Values Required

### Enum__Spec__Capability

Add one value to `sg_compute/primitives/enums/Enum__Spec__Capability.py`:

```python
OBJECT_STORAGE = 'object-storage'
```

Rationale: the S3 server is the first spec that provides a storage API surface
rather than a browser, runtime, or inference engine.  `OBJECT_STORAGE` is the
correct granularity — it covers both the S3 server and any future MinIO/GCS
shim specs.

### Enum__Spec__Nav_Group

No change needed.  `STORAGE` already exists in `Enum__Spec__Nav_Group`.

---

## 4. The Four Operation Modes

Captured as `Enum__S3_Server__Mode` inside the spec:

| Value | Meaning |
|-------|---------|
| `FULL_LOCAL` | All requests handled by the local backend.  No AWS connection. |
| `FULL_PROXY` | All requests forwarded to real AWS S3.  Pure traffic mirror + call log. |
| `HYBRID` | Implemented ops handled locally; unimplemented ops proxied to AWS. |
| `SELECTIVE` | Local storage, background sync to/from AWS S3. |

Phase 1 ships `FULL_PROXY` only.  `HYBRID` unlocks in Phase 2 as we implement
ops based on call-log data.  `FULL_LOCAL` and `SELECTIVE` follow in Phases 3–4.

The mode is set at node-create time via `Schema__S3_Server__Create__Request.mode`
and stored as an EC2 tag (`sg:s3-mode`).

---

## 5. Storage Backend Interface (Memory-FS seam)

The `sg_s3_server` package defines an abstract backend:

```python
class S3__Backend(Type_Safe):
    def put    (self, bucket: str, key: str, body: bytes, metadata: dict) -> None: ...
    def get    (self, bucket: str, key: str)                               -> bytes: ...
    def head   (self, bucket: str, key: str)                               -> dict: ...
    def delete (self, bucket: str, key: str)                               -> None: ...
    def list   (self, bucket: str, prefix: str, max_keys: int)             -> list: ...
    def create_bucket(self, bucket: str)                                   -> None: ...
    def list_buckets (self)                                                -> list: ...
```

**Phase 1 implementation:** `S3__Backend__Memory` — a plain in-memory dict.
Fast, stateless, good for call-log capture and testing.

**Memory-FS seam:** `S3__Backend__Memory_FS` is defined but contains only a
`TODO: wire Memory-FS put/get/list/delete here` comment.  The seam is locked
in place before Memory-FS integration details are confirmed.  When the human
provides the Memory-FS package name and interface (see `00__README.md` §Open
question), the implementation fills in with no structural change to the rest of
the codebase.

**Future backends:**

| Class | Backend |
|-------|---------|
| `S3__Backend__Disk` | Files on the EC2 EBS volume under `/data/s3/` |
| `S3__Backend__Vault` | Objects stored as vault files (encrypted, versioned) |
| `S3__Backend__Real_S3` | Proxy/cache — reads local, writes to real S3 |

The `S3_Server__Service` (spec side) does not know or care which backend is
active.  It only knows the `S3__Backend` interface.

---

## 6. The sg_s3_server Package (server implementation)

`sg_s3_server/` is a standalone Python package (separate from
`sg_compute_specs/`) that ships as the Docker image entrypoint.

Minimal Phase 1 surface:

```
sg_s3_server/
├── app/
│   ├── Fast_API__S3_Server.py        ← FastAPI app (not Playwright-coupled)
│   ├── routes/
│   │   ├── Routes__S3__Object.py     ← PUT/GET/DELETE/HEAD /bucket/key
│   │   ├── Routes__S3__Bucket.py     ← PUT /bucket, GET /, GET /bucket
│   │   └── Routes__S3__Call_Log.py   ← GET /call-log (UI + JSON feed)
│   └── middleware/
│       └── Call__Log__Middleware.py  ← logs every request/response
├── backends/
│   ├── S3__Backend.py                ← abstract base
│   ├── S3__Backend__Memory.py        ← Phase 1 default
│   └── S3__Backend__Memory_FS.py     ← Memory-FS seam (TODO)
├── auth/
│   └── SigV4__Validator.py           ← validates inbound SigV4 signatures
├── xml/
│   ├── S3__XML__Response.py          ← builds all XML responses
│   └── S3__XML__Error.py             ← AWS-format error envelopes
└── ui/
    └── static/                       ← S3 Browser + call log HTML/JS
```

### Phase 1 HTTP surface (minimum viable S3 API)

| Method | Path pattern | S3 op |
|--------|-------------|-------|
| GET | `/` | ListBuckets |
| PUT | `/{bucket}` | CreateBucket |
| GET | `/{bucket}?list-type=2` | ListObjectsV2 |
| PUT | `/{bucket}/{key}` | PutObject |
| GET | `/{bucket}/{key}` | GetObject |
| HEAD | `/{bucket}/{key}` | HeadObject |
| DELETE | `/{bucket}/{key}` | DeleteObject |
| GET | `/?Action=GetCallerIdentity` (STS path) | Synthetic STS response |

All responses are well-formed AWS XML.  Unimplemented ops return the correct
AWS error XML (`<Code>NotImplemented</Code>`) with HTTP 501 — not a 500, not
HTML.  boto3 gets a parseable error; it never sees an unexpected response shape.

### Call log entry (per request)

```python
class Schema__S3__Call__Log__Entry(Type_Safe):
    timestamp    : Safe_Str__Text
    method       : Safe_Str__Text
    path         : Safe_Str__Text
    aws_action   : Safe_Str__Text   # derived from method + path
    response_status : int
    response_time_ms: int
    handled_by   : Enum__S3__Handler   # LOCAL / PROXY / NOT_IMPL
    proxied      : bool = False
```

Entries are kept in-memory (circular buffer, 10 000 entries by default) and
exposed via `GET /call-log` as JSON.  The browser UI polls this endpoint.

---

## 7. The Call Log Browser UI

Static files served by the FastAPI app at `/ui/`.  Phase 1 is a single HTML
page with vanilla JS (no build step, no frameworks):

- Table of recent requests: timestamp, method, path, action, status, handler,
  timing.
- Colour coding: green (LOCAL), blue (PROXY), red (NOT_IMPL).
- Auto-refresh every 5 s.
- Stats row: total requests, not-implemented count, proxied count.

This is intentionally minimal for Phase 1.  A proper web-component version
follows once the API surface is stable.

---

## 8. The EC2 Node

The `s3_server` spec creates an EC2 instance running a single Docker container:

- Image: `sgraph/s3-server:latest` (built from `docker/s3-server/Dockerfile`)
- Port exposed: **9000** (HTTP S3 API + call log UI)
- Security group: TCP 9000 inbound from caller IP
- Instance type: `t3.small` (default — the server is lightweight)
- User data: standard Docker CE install → `docker run sgraph/s3-server:latest`

The node is ephemeral.  Storage survives only as long as the instance unless
a `FULL_LOCAL` + disk backend is configured.

---

## 9. Phased Delivery

| Phase | Scope | Gate |
|-------|-------|------|
| **Phase 1** | Spec scaffold + `FULL_PROXY` mode + call log | This brief |
| **Phase 2** | Core ops local (PutObject, GetObject, DeleteObject, HeadObject, ListObjectsV2, CreateBucket, ListBuckets) | Call log shows which ops are called first |
| **Phase 3** | `FULL_LOCAL` mode; disk and Memory-FS backends | Phase 2 coverage ≥ 90 % by call volume |
| **Phase 4** | `SELECTIVE` mode (local + S3 sync); Vault backend | Phase 3 solid |

---

## 10. Acceptance Criteria (Phase 1)

| # | Criterion |
|---|-----------|
| 1 | `boto3.client('s3', endpoint_url='http://<node-ip>:9000')` connects without error |
| 2 | Every inbound request appears in `GET /call-log` within 1 s |
| 3 | `FULL_PROXY` mode: all requests forwarded to AWS; all responses returned unchanged |
| 4 | Unimplemented ops return AWS-format XML error (`<Code>NotImplemented</Code>`, HTTP 501) |
| 5 | `sp s3 create` launches a node; `sp s3 list` shows it; `sp s3 delete` removes it |
| 6 | Call log UI accessible at `http://<node-ip>:9000/ui/` |
| 7 | All spec unit tests pass without AWS credentials or network |
| 8 | `Spec__Loader.load_all()` returns the s3_server manifest |

---

## 11. Relationship to Existing Work

| Area | Relationship |
|------|-------------|
| `sg_compute_specs/docker/` | Template: copy the folder structure, rename Docker→S3_Server |
| `sg_compute/host_plane/` | Independent; the s3 server runs as a standalone container, not via the host-control API |
| Memory-FS | Inverse relationship: Memory-FS *consumes* S3; this node *produces* S3.  Memory-FS becomes a zero-code-change consumer once its `endpoint_url` points here. |
| osbot-aws | The acid test: run osbot-aws's S3 test suite against `endpoint_url=our-node`. |
| LETS pipeline | LETS reads CloudFront logs from S3.  In a fully local deployment, this node could host the log bucket. |
