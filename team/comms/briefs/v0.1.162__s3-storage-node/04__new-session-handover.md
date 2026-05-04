# New Session Handover — S3 Storage Node

**date** 2026-05-04
**from** Developer Agent (SGraph-AI Playwright session)
**to** New Claude Code session (SG-Compute/SG-Compute__Spec__Storage-S3)
**type** Session handover — read this first

---

## What You Are Building

An **S3-compatible storage node** — a Python/FastAPI service that any boto3
client can point at via `endpoint_url` and use identically to real AWS S3,
with zero code changes on the caller side.

```python
import boto3
s3 = boto3.client('s3', endpoint_url='http://our-node:9000')
s3.put_object(Bucket='my-bucket', Key='file.txt', Body=b'hello')
obj = s3.get_object(Bucket='my-bucket', Key='file.txt')
```

This lives in the **`SG-Compute/SG-Compute__Spec__Storage-S3`** GitHub repo —
that is your primary workspace. You have write access to it.

---

## What Has Already Been Done (previous session)

The previous session (in the `the-cyber-boardroom/SGraph-AI__Service__Playwright`
repo, branch `claude/create-node-specs-eRcPG`) produced:

1. **Architecture brief** — two-layer split, four operation modes, Memory-FS
   backend seam, Phase 1 HTTP surface, call log schema, phased delivery plan.
2. **Dev task brief** — 8 concrete tasks with acceptance checklists (enums,
   primitives, schemas, service helpers, orchestrator, routes, manifest,
   Docker image stub).
3. **Memory-FS integration questions** — sent to the Memory-FS team.
4. **Memory-FS integration response** — received (full answers, working adapter
   code, `Storage_FS__S3` implementation). See §Memory-FS below.

All source files are in the **Playwright repo** — see §Where to Find Source
Files below. Clone it read-only to access them.

---

## Where to Find Source Files

**Everything is in the Playwright repo.** Clone it read-only first:

```bash
git clone https://github.com/the-cyber-boardroom/SGraph-AI__Service__Playwright /tmp/playwright-ref
# then checkout the feature branch where the brief files live:
git -C /tmp/playwright-ref fetch origin claude/create-node-specs-eRcPG
git -C /tmp/playwright-ref checkout claude/create-node-specs-eRcPG
```

### Brief files (architecture + dev tasks + handover)

| File | Content |
|------|---------|
| `team/comms/briefs/v0.1.162__s3-storage-node/00__README.md` | Goal, scope, open questions |
| `team/comms/briefs/v0.1.162__s3-storage-node/01__architecture.md` | Design decisions, phase plan |
| `team/comms/briefs/v0.1.162__s3-storage-node/02__node-spec-brief.md` | **8 dev tasks + acceptance checklists — read this to build** |
| `team/comms/briefs/v0.1.162__s3-storage-node/03__memory-fs-integration-questions.md` | Questions sent to Memory-FS team |
| `team/comms/briefs/v0.1.162__s3-storage-node/04__new-session-handover.md` | This file |

### Memory-FS source files

| File | Content |
|------|---------|
| `team/humans/dinis_cruz/briefs/05/04/memory-fs-integration-response.md` | **Full Memory-FS answers — read before writing any backend code** |
| `team/humans/dinis_cruz/briefs/05/04/Storage_FS__S3.py` | Actual `Storage_FS__S3` implementation (working code) |
| `team/humans/dinis_cruz/briefs/05/04/v0.27.2__arch-brief__s3-compatible-api-full-boto3-transparency.md` | Original human brief |

### Code patterns to copy

| Path | Why |
|------|-----|
| `sg_compute_specs/docker/` | **The canonical template.** Copy its folder structure, rename Docker→S3_Server. |
| `sg_compute/primitives/enums/Enum__Spec__Capability.py` | Add `OBJECT_STORAGE = 'object-storage'` here (needs a PR to the Playwright repo). |
| `sg_compute/core/spec/schemas/Schema__Spec__Manifest__Entry.py` | The manifest schema your `manifest.py` must instantiate. |
| `sg_compute/core/spec/Spec__Loader.py` | Discovers specs — your manifest must be discoverable by it. |
| `.claude/CLAUDE.md` | **Project rules — non-negotiable.** Read before writing a single line. |

---

## Architecture (Two-Layer Split)

```
sg_compute_specs/s3_server/     ← Node Spec (thin: launch, connect, teardown)
sg_s3_server/                   ← S3 server implementation (HTTP, call log, backends)
```

The spec layer follows the docker spec pattern exactly. The server layer is a
new standalone package. Keep them strictly separated — the spec does not import
from `sg_s3_server`.

---

## Memory-FS Integration — Complete Details

The Memory-FS team provided full answers. Here is the summary you need.

### Package

```bash
pip install memory-fs
```

```python
from memory_fs.storage_fs.Storage_FS import Storage_FS
from memory_fs.storage_fs.Storage_FS__S3 import Storage_FS__S3
# Storage_FS__Memory also exists for in-memory backend
```

GitHub: https://github.com/owasp-sbot/Memory-FS

### Interface (what matters)

```python
class Storage_FS(Type_Safe):
    def file__save        (self, path, data: bytes) -> bool
    def file__bytes       (self, path)              -> Optional[bytes]
    def file__str         (self, path)              -> Optional[str]
    def file__json        (self, path)              -> Optional[dict]
    def file__exists      (self, path)              -> bool
    def file__delete      (self, path)              -> bool
    def file__metadata    (self, path)              -> Optional[dict]
    def file__metadata_update(self, path, metadata) -> bool
    def file__size        (self, path)              -> Optional[int]
    def file__last_modified(self, path)             -> Optional[str]
    def files__paths      (self)                    -> List[Safe_Str__File__Path]
    def folder__files     (self, folder_path)       -> List[Safe_Str__File__Path]
    def clear             (self)                    -> bool
    def file__copy        (self, src, dest)         -> bool
    def file__move        (self, src, dest)         -> bool
```

### Addressing model

Memory-FS is flat-path. Map S3 `bucket/key` like this:

```python
path = Safe_Str__File__Path(f"{bucket}/{key}")
```

Bucket registry is a separate JSON file (`__buckets__.json`) stored in the
same storage.

### The adapter to write (`S3__Backend__Storage_FS`)

See `/tmp/playwright-ref/team/humans/dinis_cruz/briefs/05/04/memory-fs-integration-response.md`
§6 for the complete implementation. The key structure:

```python
class S3__Backend__Storage_FS(S3__Backend):
    storage         : Storage_FS    = None
    bucket_registry : BucketRegistry = None

    def setup(self, storage_type='memory', **config): ...
    def put   (self, bucket, key, body, metadata):    ...
    def get   (self, bucket, key) -> bytes:           ...
    def head  (self, bucket, key) -> dict:            ...
    def delete(self, bucket, key):                    ...
    def list  (self, bucket, prefix, max_keys) -> list: ...
    def create_bucket(self, bucket):                  ...
    def list_buckets(self) -> list:                   ...
```

### Thread safety

Storage_FS is NOT thread-safe for writes. Wrap write operations with
`threading.RLock()`. Reads can be concurrent. See
`/tmp/playwright-ref/team/humans/dinis_cruz/briefs/05/04/memory-fs-integration-response.md` §7.

---

## Phase 1 Scope (what to build first)

Phase 1 = **call log + full proxy mode**. Everything else is Phase 2+.

### The spec layer (`sg_compute_specs/s3_server/`) — 8 tasks

Follow `/tmp/playwright-ref/team/comms/briefs/v0.1.162__s3-storage-node/02__node-spec-brief.md` exactly. Summary:

| Task | What |
|------|------|
| 0 | Add `OBJECT_STORAGE = 'object-storage'` to `Enum__Spec__Capability` in Playwright repo |
| 1 | Enums + primitives (Mode, Backend, State, Handler; Stack__Name, IP__Address) |
| 2 | Schemas + collections (Create__Request/Response, Info, List, Delete, Health) |
| 3 | Service helpers (AWS__Client, SG, AMI, Instance, Tags, Mapper, User_Data, Launch, Health__Checker, Caller__IP, Name__Gen) |
| 4 | Orchestrator (`S3_Server__Service`) |
| 5 | FastAPI routes (`Routes__S3_Server__Stack`) |
| 6 | Manifest (`manifest.py`) |
| 7 | Tests (30+ unit tests, no AWS, no mocks) |
| 8 | Docker image stub (`docker/s3-server/Dockerfile`) |

### The server layer (`sg_s3_server/`) — Phase 1 minimum

```
sg_s3_server/
├── app/
│   ├── Fast_API__S3_Server.py          ← FastAPI app
│   ├── routes/
│   │   ├── Routes__S3__Object.py       ← PUT/GET/DELETE/HEAD /{bucket}/{key}
│   │   ├── Routes__S3__Bucket.py       ← PUT /{bucket}, GET /
│   │   └── Routes__S3__Call_Log.py     ← GET /call-log
│   └── middleware/
│       └── Call__Log__Middleware.py    ← logs every request/response
├── backends/
│   ├── S3__Backend.py                  ← abstract base (Type_Safe)
│   ├── S3__Backend__Memory.py          ← in-memory dict (Phase 1 default)
│   └── S3__Backend__Storage_FS.py      ← Memory-FS adapter
├── xml/
│   ├── S3__XML__Response.py            ← well-formed AWS XML responses
│   └── S3__XML__Error.py               ← AWS error envelope
└── ui/
    └── static/                         ← call log browser (plain HTML/JS)
```

### Phase 1 HTTP surface (minimum viable)

| Method | Path | S3 operation |
|--------|------|--------------|
| GET | `/` | ListBuckets |
| PUT | `/{bucket}` | CreateBucket |
| GET | `/{bucket}?list-type=2` | ListObjectsV2 |
| PUT | `/{bucket}/{key}` | PutObject |
| GET | `/{bucket}/{key}` | GetObject |
| HEAD | `/{bucket}/{key}` | HeadObject |
| DELETE | `/{bucket}/{key}` | DeleteObject |
| GET | `/?Action=GetCallerIdentity` | Synthetic STS response |

All unimplemented ops return `<Code>NotImplemented</Code>` XML with HTTP 501
(never 500, never HTML — boto3 must be able to parse the error).

---

## Non-Negotiable Code Rules

These come from the Playwright repo's `CLAUDE.md`. They apply here too.

1. **All classes extend `Type_Safe`** from `osbot_utils` — no plain Python classes, no Pydantic, no Literals.
2. **One class per file** — filename matches class name exactly.
3. **`__init__.py` files stay empty** — import from fully-qualified paths.
4. **No mocks in tests** — use real subclasses with fake inputs.
5. **No raw primitives** — use `Safe_Str__*` / `Enum__*` / collection subclasses for attributes.
6. **`═══` 80-char section headers** in every file.
7. **Inline comments only** — no docstrings, ever.
8. **Every route returns `.json()` on a Type_Safe schema** — no raw dicts.
9. **No AWS credentials in Git** — never in schemas, user-data, or any committed file.
10. **Section prefix `s3srv`** — e.g. `Stack__Naming(section_prefix='s3srv')`. GroupName must NOT start with `sg-`.

---

## First Steps for This Session

1. Clone the Playwright repo read-only and check out the feature branch:
   ```bash
   git clone https://github.com/the-cyber-boardroom/SGraph-AI__Service__Playwright /tmp/playwright-ref
   git -C /tmp/playwright-ref fetch origin claude/create-node-specs-eRcPG
   git -C /tmp/playwright-ref checkout claude/create-node-specs-eRcPG
   ```
2. Read (in order):
   - `/tmp/playwright-ref/team/comms/briefs/v0.1.162__s3-storage-node/00__README.md`
   - `/tmp/playwright-ref/team/comms/briefs/v0.1.162__s3-storage-node/01__architecture.md`
   - `/tmp/playwright-ref/team/comms/briefs/v0.1.162__s3-storage-node/02__node-spec-brief.md` ← the task list
   - `/tmp/playwright-ref/team/humans/dinis_cruz/briefs/05/04/memory-fs-integration-response.md`
   - `/tmp/playwright-ref/team/humans/dinis_cruz/briefs/05/04/Storage_FS__S3.py`
3. Read `/tmp/playwright-ref/.claude/CLAUDE.md` — the non-negotiable code rules.
4. Read every file under `/tmp/playwright-ref/sg_compute_specs/docker/` — this is your template.
5. Create a branch `claude/s3-storage-node-phase1` in **this** repo (`SG-Compute/SG-Compute__Spec__Storage-S3`).
6. Start with Task 0 (adding `OBJECT_STORAGE` to `Enum__Spec__Capability`) — if you have write access to the Playwright repo, do it there; if not, note it as a dependency and proceed with Tasks 1–8 in this repo.
7. Build the `sg_s3_server/` server package alongside the spec.

---

## Key Decisions Already Made

| Decision | Rationale |
|----------|-----------|
| Two-layer split (spec + server) | Keeps the spec thin (matches docker/ollama scope); server evolves independently |
| Memory-FS as storage backend | `Storage_FS` interface maps cleanly to S3 `put/get/head/delete/list`; flat-path with `bucket/key` namespace works |
| `Storage_FS__Memory` as Phase 1 default | Fast, stateless, no deps — good for call-log capture and testing |
| `Storage_FS__S3` for FULL_PROXY/SELECTIVE | Already implemented by Memory-FS team (see `/tmp/playwright-ref/team/humans/dinis_cruz/briefs/05/04/Storage_FS__S3.py`) |
| Call log in-memory circular buffer (10k entries) | Simple, fast; `GET /call-log` JSON feed polled by browser UI |
| `OBJECT_STORAGE` capability (not `S3_API_COMPAT`) | Correct granularity — covers S3 server + any future MinIO/GCS shim |
| Section prefix `s3srv` | Short enough for tag values; avoids `sg-*` SG naming collision |
| Port 9000 | Matches MinIO convention; users already know it |
| `t3.small` default instance | S3 server is lightweight; RAM dominated by in-memory backend |

---

## Acceptance Criteria (Phase 1 done when all pass)

| # | Test |
|---|------|
| 1 | `boto3.client('s3', endpoint_url='http://<node>:9000')` connects without error |
| 2 | `s3.put_object` + `s3.get_object` round-trip returns identical bytes |
| 3 | Every request appears in `GET /call-log` within 1 s |
| 4 | Unimplemented op returns `<Code>NotImplemented</Code>` XML, HTTP 501 |
| 5 | `Spec__Loader.load_all()` returns `s3_server` manifest |
| 6 | All 30+ spec unit tests pass without AWS credentials or network |
| 7 | Browser UI at `/ui/` shows call log with colour-coded rows |
| 8 | `S3__Backend__Storage_FS` adapter passes put/get/head/delete/list unit tests |

---

## Pending Dependencies

- **`OBJECT_STORAGE` enum** — needs to be added to `Enum__Spec__Capability` in
  the Playwright repo (`sg_compute/primitives/enums/Enum__Spec__Capability.py`).
  If you don't have write access to that repo, build everything else first and
  note this as an open PR.
- **`Enum__Stack__Type.S3_SERVER`** — needs adding to
  `sgraph_ai_service_playwright__cli/catalog/enums/Enum__Stack__Type.py` in the
  Playwright repo (consumed by the event bus `emit` in the orchestrator).
  Same caveat.

---

## Questions / Contact

If something is unclear about the architecture, check:
- `/tmp/playwright-ref/team/comms/briefs/v0.1.162__s3-storage-node/01__architecture.md` — design rationale
- `/tmp/playwright-ref/team/comms/briefs/v0.1.162__s3-storage-node/02__node-spec-brief.md` — task details
- `/tmp/playwright-ref/sg_compute_specs/docker/` — the living reference implementation
