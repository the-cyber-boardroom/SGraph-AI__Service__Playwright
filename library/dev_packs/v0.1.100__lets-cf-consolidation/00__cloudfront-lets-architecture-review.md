# CloudFront LETS Pipeline — Architecture Review

**Author:** Architect (Explorer session)
**Date:** 2026-04-27
**Branch:** `claude/spell-commands-observability-vO6wV` (synced with `dev` HEAD `3ba5878`)
**Repo version:** `v0.1.101` (root) / `v0.1.100` (package)
**Scope:** End-to-end picture of the CloudFront real-time logs pipeline — the system the next planning round (`SG_Send__Orchestrator` + `sg-send sync` family) will sit on top of.

> Grounding: every claim here is verified against the v0.1.31 reality docs (files 09/10/11), the source on `dev` (incl. commit `7527597` and the freshly-merged `runs/` package from commit `c9b8e6a`), and the planning handover at `team/humans/dinis_cruz/claude-code-web/04/27/09/`.

---

## 1. The 30-second story

A user hits `sgraph.ai`. CloudFront serves the request from an edge location and emits a real-time log line per request. AWS Firehose buffers those log lines and writes them as gzipped TSV files to an S3 bucket — roughly 300–400 small `.gz` files per day. None of this is read until the operator runs the **LETS pipeline**: a CLI suite (`sp el lets cf …`) that lists, fetches, parses, classifies, and indexes those events into an **Ephemeral Kibana** stack on EC2, behind an nginx/TLS proxy reachable from the operator's IP only. Three indices result — inventory metadata, parsed events, and a pipeline-runs journal — plus two auto-imported dashboards. The stack is disposable; the S3 bucket is the source of truth; everything Kibana holds can be rebuilt from S3.

---

## 2. End-to-end data flow

The full path from a user's browser to a chart panel in Kibana:

```
                                  ┌───────────────────┐
                                  │   User browser    │
                                  │  (HTTP request)   │
                                  └─────────┬─────────┘
                                            │  GET /some/path
                                            ▼
                              ┌─────────────────────────┐
                              │   CloudFront edge POP   │   e.g. HIO52-P4
                              │   (sgraph.ai distrib.)  │
                              └────┬────────────────┬───┘
                          serves   │                │   real-time log line
                          response │                │   (38 TSV fields)
                                   ▼                ▼
                              ┌────────┐    ┌──────────────────┐
                              │ user   │    │   AWS Firehose   │
                              │ origin │    │   (buffer +      │
                              └────────┘    │    gzip + write) │
                                            └────────┬─────────┘
                                                     │  every ~60s OR
                                                     │  ~5 MB buffer
                                                     ▼
                          ┌────────────────────────────────────────────┐
                          │  S3 — 745506449035--sgraph-send-cf-logs    │
                          │       --eu-west-2                          │
                          │                                            │
                          │  cloudfront-realtime/{YYYY}/{MM}/{DD}/{HH}/│
                          │     EXXXX.{date}.{uuid}.gz   ~1–2 KB each  │
                          │     ~300–400 objects/day total              │
                          └────────┬───────────────────────────────────┘
                                   │
                                   │  ┄┄┄┄┄┄┄┄┄┄ THE GAP ┄┄┄┄┄┄┄┄┄┄
                                   │  Operator runs `sp el lets cf …`
                                   │  Without that, nothing is read.
                                   ▼
                  ╔══════════════════════════════════════════════════════╗
                  ║              LETS PIPELINE  (the bridge)             ║
                  ║                                                      ║
                  ║   L oad     —  list / fetch from S3                  ║
                  ║   E xtract  —  gunzip + TSV parse + bot classify     ║
                  ║   T ransform — (deferred — Kibana aggregations)      ║
                  ║   S ave     —  bulk-index into Elasticsearch         ║
                  ╚══════════════╤═══════════════════════════════════════╝
                                 │
                                 ▼
        ┌─────────────────────────────────────────────────────────────┐
        │   Ephemeral Kibana stack on EC2 (m6i.xlarge)                │
        │                                                             │
        │     nginx:443  TLS termination (self-signed, SAN = pub-IP)  │
        │       │  /         → kibana:5601                            │
        │       │  /_elastic → elasticsearch:9200                     │
        │       ▼                                                     │
        │   ┌─────────────┐                ┌──────────────┐           │
        │   │  Kibana     │   Discover/    │ Elasticsearch│           │
        │   │  (8.13.4)   │◄───── search ──┤  (8.13.4)    │           │
        │   │             │                │              │           │
        │   │  Dashboards │                │  Indices:    │           │
        │   │   - inv-overview   (5 viz)   │   sg-cf-     │           │
        │   │   - events-overview (6 viz)  │     inventory│           │
        │   └─────────────┘                │     -{date}  │           │
        │                                  │   sg-cf-     │           │
        │                                  │     events   │           │
        │                                  │     -{date}  │           │
        │                                  │   sg-pipeline│           │
        │                                  │     -runs    │           │
        │                                  │     -{date}  │           │
        │                                  └──────────────┘           │
        └────────────────────────────┬────────────────────────────────┘
                                     │
                                     │  HTTPS, operator's /32 only
                                     ▼
                              ┌─────────────┐
                              │  Operator's │
                              │   browser   │
                              └─────────────┘
```

Everything left of "THE GAP" runs continuously and costs ~nothing. Everything right of it is opt-in: the operator chooses when to spin a stack up, when to load, and tears down when done.

---

## 3. The LETS principle (why the pipeline is split this way)

**Verbatim from the user's handover (`01__history-and-context.md`):**

> *"Persist Everything Important BEFORE Indexing Anything. Elasticsearch is NOT the source of truth — it is an index, a cache, a search layer, a visualisation layer."*

Operationally that means:

| Stage | Responsibility | Persisted to |
|-------|----------------|--------------|
| **L** Load | Pull raw bytes from the authoritative source | S3 (already there — Firehose did it) |
| **E** Extract | Decode bytes into typed records | (in-memory only for now — slice 3 may persist) |
| **T** Transform | Enrich, aggregate, derive | (deferred — Kibana aggregations cover this today) |
| **S** Save | Make the records queryable | Elasticsearch indices in the ephemeral stack |

**Two consequences fall out of this:**

1. **Every `load` has a matched `wipe`.** Kibana indices are disposable. Re-running the load from S3 always reconstructs them. This is enforced as a rule across both slices.
2. **The S3 bucket is the only thing that must not be lost.** The Kibana stack is cattle, not pets — the AMI workflow + the 1-hour auto-terminate exist because losing it is cheap.

---

## 4. Component decomposition

The pipeline today has **three slices** and a **shared journal**, all under `sgraph_ai_service_playwright__cli/elastic/lets/`.

```
elastic/lets/
├── Call__Counter.py           ← Phase A: shared counter (s3_calls, elastic_calls)
├── Step__Timings.py           ← Phase A: per-file timing (5 measured steps)
│
├── runs/                      ← Phase B: pipeline journal (NEW, commit c9b8e6a)
│   ├── enums/Enum__Pipeline__Verb.py
│   ├── schemas/Schema__Pipeline__Run.py
│   ├── collections/List__Schema__Pipeline__Run.py
│   └── service/Pipeline__Runs__Tracker.py
│
└── cf/                        ← CloudFront-specific implementations
    ├── inventory/             ── Slice 1: S3 metadata → sg-cf-inventory-{date}
    ├── events/                ── Slice 2: .gz content → sg-cf-events-{date}
    └── sg_send/               ── Phase A.5: SGraph-Send convenience wrapper
                                  diagnostic-only today (files / view)
                                  SG_Send__Orchestrator is FORWARD-DECLARED
                                  but does not yet exist
```

### 4.1 Slice boundaries (why each slice is its own folder)

| Slice | Reads from | Writes to | Why it's separate |
|-------|------------|-----------|-------------------|
| **inventory** | S3 `ListObjectsV2` (no GetObject) | `sg-cf-inventory-{date}` | Proves the data path — pagination, ES bulk-post, dashboard import — without any binary content. Forward-declares `content_processed: false` on every doc as the manifest hook for slice 2. |
| **events** | S3 `GetObject` per `.gz` + reads slice 1's manifest | `sg-cf-events-{date}` + flips inventory's `content_processed=true` | Adds the heavy lifting — gunzip, 38-field TSV parse, bot classification — and consumes slice 1's manifest as its work queue (`--from-inventory` mode). |
| **runs** (journal) | nothing | `sg-pipeline-runs-{date}` | Cross-cutting Phase B addition: every `load()` records one journal doc keyed on `run_id`. Single writer = `Pipeline__Runs__Tracker`. Date keyed on `started_at[:10]` so a midnight-crossing run lands in the day it began. |
| **sg_send** | reads inventory + events | nothing today (read-only diagnostic shortcuts) | Hardcodes SGraph-Send specifics (bucket name, year defaulting to 2026) so the generic slices stay bucket-agnostic. **Future home of `SG_Send__Orchestrator`.** |

### 4.2 The "shared infra" classes

```
                       ┌────────────────────────────┐
                       │   Call__Counter (Phase A)  │
                       │   s3_calls   elastic_calls │
                       └──────────┬─────────────────┘
                                  │ injected once-per-run, shared across:
                  ┌───────────────┼───────────────────┬─────────────────────┐
                  ▼               ▼                   ▼                     ▼
    ┌───────────────────┐  ┌────────────────┐  ┌──────────────────┐  ┌──────────────────┐
    │ S3__Inventory__   │  │ S3__Object__   │  │ Inventory__HTTP__│  │ Inventory__      │
    │   Lister          │  │   Fetcher      │  │   Client         │  │ Manifest__       │
    │ (paginate boundary│  │ (GetObject     │  │ (every ES/Kibana │  │   Updater        │
    │  for boto3)       │  │  boundary)     │  │  HTTP call)      │  │ (mark/reset)     │
    └───────────────────┘  └────────────────┘  └──────────────────┘  └──────────────────┘
              ▲                    ▲                    ▲                      ▲
              │                    │                    │                      │
              └─────── Slice 1 ────┘                    └──── Slice 1 + 2 ─────┘
                                   │
                                   └──── Slice 2 ────────────────────────────────
```

Today, each loader auto-instantiates its own `Call__Counter` (Type_Safe default), so tallies are per-loader. The forward declaration in `Call__Counter.py` lines 15–17 reads:

```
SG_Send__Orchestrator — constructs ONE counter, injects into every
                       collaborator so the final tallies span the whole run
```

This is the architectural seam the next planning round fills.

```
                       ┌─────────────────────────────────┐
                       │   Step__Timings (Phase A)       │
                       │   s3_get_ms, gunzip_ms,         │
                       │   parse_ms, bulk_post_ms,       │
                       │   manifest_update_ms            │
                       └─────────────┬───────────────────┘
                                     │ one per file processed
                                     ▼
                              Progress__Reporter
                              (no-op base; CLI overrides
                              with Console__Progress__Reporter
                              for Rich output)
```

```
                       ┌─────────────────────────────────┐
                       │   Pipeline__Runs__Tracker       │  Phase B (new)
                       │   (single writer to             │
                       │    sg-pipeline-runs-{date})     │
                       └─────────────┬───────────────────┘
                                     │ called once at end of every load()
                                     ▼
                       Schema__Pipeline__Run
                       _id = run_id (overwrite-in-place idempotent)
```

---

## 5. Slice 1 in detail — `sp el lets cf inventory`

```
                                ┌──────────────────────────────────┐
                                │  sp el lets cf inventory load    │
                                │  [--prefix YYYY/MM/DD/HH]        │
                                │  [--all] [--max-keys N]          │
                                │  [--dry-run] [--run-id ID]       │
                                └────────────────┬─────────────────┘
                                                 │
                                                 ▼
                                        ┌────────────────┐
                                        │ Inventory__    │
                                        │   Loader       │  (orchestrator)
                                        └─────┬──────────┘
                                              │
      ┌────────────────────┬───────────────────┼───────────────────┬─────────────────────┐
      ▼                    ▼                   ▼                   ▼                     ▼
┌───────────┐      ┌──────────────┐    ┌─────────────┐    ┌──────────────────┐  ┌────────────────┐
│ Elastic__ │      │ S3__         │    │ Run__Id__   │    │ Inventory__HTTP__│  │ CF__Inventory  │
│ Service   │      │ Inventory__  │    │ Generator   │    │ Client           │  │ __Dashboard__  │
│ .get_     │      │ Lister       │    │ ISO-ts +    │    │ ensure_data_view │  │ Builder        │
│ stack_    │      │ ListObjects  │    │ slug + 4hex │    │ bulk_post        │  │ (5-panel       │
│ info()    │      │ V2 paginator │    │             │    │ delete / count   │  │  ndjson)       │
└───────────┘      └──────────────┘    └─────────────┘    └──────────────────┘  └────────────────┘
                          │                                       │
                          │ for each S3 obj:                      │
                          │   parse Firehose-embedded             │
                          │   timestamp from filename             │
                          │   build Schema__S3__Object__Record    │
                          │   (38 fields incl.                    │
                          │   content_processed=false             │
                          │   forward-declared)                   │
                          │                                       │
                          │ group by delivery_at[:10]             │
                          └──────────────┬────────────────────────┘
                                         │
                                         ▼
                    ┌────────────────────────────────────────┐
                    │  bulk-post per day,  _id = etag        │
                    │  → sg-cf-inventory-{YYYY-MM-DD}        │
                    │     (re-runs dedupe at index time)     │
                    └────────────────────────────────────────┘
```

**Wipe (matched pair, idempotent):**

1. `DELETE` every `sg-cf-inventory-*` index by name (wildcard DELETE blocked by ES `action.destructive_requires_name=true` — this was a real bug fix)
2. Delete data view (`sg-cf-inventory-*` and the legacy `sg-cf-inventory` defensively)
3. Delete dashboard saved-object + the 5 visualisation saved-objects (deterministic ids in `CF__Inventory__Dashboard__Ids`)

**Performance proof**: ~425 docs / day in ~2 seconds. 150 unit tests, zero mocks.

---

## 6. Slice 2 in detail — `sp el lets cf events`

This is the heavy slice — the one that actually reads `.gz` content.

```
                                ┌───────────────────────────────────────────┐
                                │ sp el lets cf events load                 │
                                │   [--prefix YYYY/MM/DD]                   │
                                │   [--from-inventory]   ← manifest mode    │
                                │   [--skip-processed]   ← alt dedup        │
                                │   [--max-files N] [--dry-run]             │
                                └─────────────────────┬─────────────────────┘
                                                      │
                                                      ▼
                                           ┌────────────────────┐
                                           │ Events__Loader     │  (orchestrator)
                                           └─────────┬──────────┘
                                                     │
                                       ┌─────────────┴───────────────┐
                                       │  build queue (two modes)    │
                                       └──┬──────────────────────────┘
                                          │
              ┌───────────────────────────┴──────────────────────────────┐
              ▼                                                          ▼
   ┌───────────────────────┐                                ┌────────────────────────┐
   │ S3__Inventory__Lister │  (default)                     │ Inventory__Manifest__  │
   │ list cloudfront-      │                                │ Reader                 │
   │ realtime/{prefix}/    │                                │ ES query for           │
   │                       │                                │ content_processed=     │
   │                       │                                │   false in inventory   │
   └───────────┬───────────┘                                └────────────┬───────────┘
               │                                                         │
               └──────────────┬──────────────────────────────────────────┘
                              │
                              ▼
                ┌─────────────────────────────┐
                │  per-file loop              │
                │                             │
                │  ┌────────────────────────┐ │
                │  │ S3__Object__Fetcher    │ │ ← Step__Timings.s3_get_ms
                │  │ get_object_bytes(...)  │ │
                │  └────────────┬───────────┘ │
                │               │ raw bytes   │
                │               ▼             │
                │  ┌────────────────────────┐ │
                │  │ gzip.decompress        │ │ ← Step__Timings.gunzip_ms
                │  └────────────┬───────────┘ │
                │               │ TSV string  │
                │               ▼             │
                │  ┌────────────────────────┐ │
                │  │ CF__Realtime__Log__    │ │ ← Step__Timings.parse_ms
                │  │   Parser.parse()       │ │
                │  │   - TSV split          │ │
                │  │   - URL-decode UA      │ │
                │  │   - trim referer       │ │
                │  │   - status_class       │ │
                │  │   - cache_hit flag     │ │
                │  │   - Bot__Classifier:   │ │
                │  │       28 named regexes │ │
                │  │       + 5 generic      │ │
                │  │       word-bounded     │ │
                │  │       indicators       │ │
                │  │       → Enum__CF__Bot__│ │
                │  │         Category       │ │
                │  └────────────┬───────────┘ │
                │               │             │
                │               │ List__Schema│
                │               │ __CF__Event │
                │               │ __Record    │
                │               │ (38 fields  │
                │               │  per row)   │
                │               ▼             │
                │  stamp source_bucket, key,  │
                │  etag, line_index,          │
                │  doc_id={etag}__{idx},      │
                │  pipeline_run_id, loaded_at │
                │               │             │
                │               ▼             │
                │  group by timestamp[:10]    │
                │               │             │
                │               ▼             │
                │  ┌────────────────────────┐ │
                │  │ Inventory__HTTP__Client│ │ ← Step__Timings.bulk_post_ms
                │  │ bulk-post per day      │ │
                │  │ → sg-cf-events-{date}  │ │
                │  │   _id=doc_id (per-     │ │
                │  │   event idempotent)    │ │
                │  └────────────┬───────────┘ │
                │               │             │
                │               ▼             │
                │  ┌────────────────────────┐ │
                │  │ Inventory__Manifest__  │ │ ← Step__Timings.manifest_update_ms
                │  │   Updater              │ │
                │  │ mark_processed(etag,   │ │
                │  │   run_id) → flips      │ │
                │  │ inventory doc's        │ │
                │  │ content_processed=true │ │
                │  └────────────────────────┘ │
                │                             │
                └─────────────────────────────┘
                              │
                              ▼
                   ┌──────────────────────────┐
                   │ Progress__Reporter hooks:│
                   │   on_queue_built         │
                   │   on_skip_filter_done    │
                   │   on_file_done           │
                   │   on_file_error          │
                   │   on_load_complete       │
                   │ (CLI uses Rich subclass) │
                   └──────────────────────────┘
```

**Wipe (4-step, idempotent):**

1. Delete every `sg-cf-events-*` index by name
2. Delete data view `sg-cf-events-*`
3. Delete dashboard `sg-cf-events-overview` + 6 visualisation saved-objects
4. **`_update_by_query`** — flips every `content_processed=true` back to `false` in inventory, so the next `--from-inventory` run finds the full queue again. This is the cross-slice link.

**Performance proof**: 565 events from 50 `.gz` files in ~12 seconds. 201 unit tests, zero mocks.

---

## 7. The two work-queue modes — and why both exist

```
   ┌──── Default mode ────────────────┐    ┌──── --from-inventory mode ─────┐
   │                                  │    │                                │
   │  S3 ListObjectsV2                │    │  ES query inventory index for  │
   │   ↓                              │    │  content_processed=false       │
   │  Filter to {prefix}              │    │   ↓                            │
   │   ↓                              │    │  Sort by delivery_at desc      │
   │  Apply --max-files               │    │   ↓                            │
   │   ↓                              │    │  Apply --max-files             │
   │  Process every file in result    │    │   ↓                            │
   │                                  │    │  Process every file in result  │
   │  ✱ Re-running re-processes       │    │  ✱ Re-running skips already-   │
   │    every file unless --skip-     │    │    processed files automatically│
   │    processed is set              │    │    (idempotent by construction)│
   └──────────────────────────────────┘    └────────────────────────────────┘
```

`--skip-processed` is the third mode — it pre-queries inventory for already-processed etags and filters them out of the default mode's queue. **It was bug-fixed on commit `567602b`** to read from the inventory manifest, not the events index. (The events index can have multiple docs per file — one per line — so it's the wrong place to dedup at the file level.)

**Architectural recommendation when designing `sg-send sync`:** `--from-inventory` is the right default. It uses the manifest the way the manifest was designed to be used.

---

## 8. The cross-slice link in pictures

This is the single most important diagram for understanding why the slices aren't independent:

```
   ┌─────────────────────────────────────────────────────────────────────┐
   │  sg-cf-inventory-2026-04-27       (one doc per .gz S3 object)       │
   │                                                                     │
   │   _id=etagA  content_processed=false                                │
   │   _id=etagB  content_processed=false        ←── slice 1 writes      │
   │   _id=etagC  content_processed=false             "false" forward-   │
   │   …                                              declaring slice 2  │
   └─────────────────────────────────────────────────────────────────────┘
                                  ▲                         │
                                  │                         │
                    ┌─────────────┘                         │  --from-inventory
        slice 2     │  Inventory__Manifest__Updater         │  reads where
        AFTER       │  .mark_processed(etagA, run_id)       │  processed=false
        each file:  │  flips it ─→ content_processed=true   │
                    │  + content_extract_run_id stamped     ▼
                    │                          ┌────────────────────────┐
                    │                          │  Inventory__Manifest__ │
                    │                          │   Reader               │
                    │                          │  builds work queue     │
                    │                          │  from unprocessed rows │
                    │                          └────────────────────────┘
                    │
   ┌─────────────────────────────────────────────────────────────────────┐
   │  sg-cf-events-2026-04-27        (one doc per TSV line)              │
   │                                                                     │
   │   _id={etagA}__0  url=/foo  status=200  bot_cat=HUMAN               │
   │   _id={etagA}__1  url=/bar  status=404  bot_cat=BOT_KNOWN           │
   │   _id={etagA}__2  …                                                 │
   │   …                                                                 │
   └─────────────────────────────────────────────────────────────────────┘

   AND THEN: Pipeline__Runs__Tracker writes ONE doc to:
   ┌─────────────────────────────────────────────────────────────────────┐
   │  sg-pipeline-runs-2026-04-27    (one doc per LETS run)              │
   │                                                                     │
   │   _id=run_id  verb=events-load  files_processed=50  events=565      │
   │   _id=run_id  s3_calls=51 elastic_calls=212 duration_ms=12_034      │
   └─────────────────────────────────────────────────────────────────────┘
```

**Idempotency keys at every layer**:

| Layer | `_id` | What this enables |
|-------|-------|-------------------|
| inventory doc | `etag` | Re-listing same S3 object → upsert, no duplication |
| event doc | `{etag}__{line_index}` | Re-parsing same `.gz` → upsert per line, no duplication |
| pipeline-run journal | `run_id` | Re-recording same run → overwrite-in-place |

The whole pipeline is **safe to re-run** on any subset, in any order. That's the property the `SG_Send__Orchestrator` will lean on for its `sync` semantics.

---

## 9. CLI surface — what exists today

```
sp el                                    Ephemeral Kibana stack lifecycle
sp el create [--seed]                    Cold path (~3 min)
sp el create-from-ami [--wait]           Fast path (~80s, needs an AMI)
sp el ami create / list / delete         AMI lifecycle (~10–15 min to bake)
sp el list / info / health               Inspect a running stack
sp el connect / exec --                  SSM access (no SSH)
sp el dashboard list / export / import   Saved-object snapshots
sp el data-view list / export / import   Saved-object snapshots
sp el wipe                               Drop synthetic seed data
sp el harden                             Re-apply nav harden if needed
sp el delete --all -y                    Tear it down
sp el lets                               LETS pipelines mount point
sp el lets cf                            CloudFront LETS namespace
sp el lets cf inventory                  Slice 1
sp el lets cf inventory load             ListObjectsV2 → sg-cf-inventory-{date}
sp el lets cf inventory wipe             Drop indices + data view + dashboard
sp el lets cf inventory list             Distinct pipeline_run_id values
sp el lets cf inventory health           3 plumbing checks
sp el lets cf events                     Slice 2
sp el lets cf events load                GetObject → parse → sg-cf-events-{date}
sp el lets cf events wipe                + resets inventory manifest (cross-slice)
sp el lets cf events list                Distinct pipeline_run_id values
sp el lets cf events health              4 checks (incl. inventory-link %)
sp el lets cf sg-send                    SGraph-Send convenience wrappers
sp el lets cf sg-send files <date>       Inventory query, no S3
sp el lets cf sg-send view  <key>        One .gz, raw TSV or --table parsed
```

**What does NOT exist** (and is the subject of the upcoming planning round):

```
sp el lets cf sg-send sync       ← Tier 1 — SG_Send__Orchestrator wraps both slices
sp el lets cf sg-send status     ← Tier 1 — read-only health across both slices
sp el lets cf sg-send backfill   ← Tier 2 — date-range walker
sp el lets cf sg-send report     ← Tier 3 — daily traffic summary, read-only
sp el lets cf sg-send wipe-all   ← Tier 3 — convenience over both wipes
sp el lets cf sg-send runs       ← Phase B follow-on — read sg-pipeline-runs-*
                                   (Enum__Pipeline__Verb already declares the
                                   verbs; the read-side CLI does not yet exist)
```

---

## 10. Operator's daily recipe (today)

```
   $ export AWS_DEFAULT_REGION=eu-west-2
   $ export SG_ELASTIC_PASSWORD="MyStrong_Pass-123"
   │
   │  morning
   ▼
   sp el create-from-ami --wait                  (~80 seconds)
   │
   ▼  manual two-step:
   sp el lets cf inventory load                  (~2 sec, 425 docs)
   sp el lets cf events load --from-inventory    (~12 sec, 565 events)
   │
   ▼  read in Kibana (operator's IP only)
   https://{public-ip}/  →  Dashboards
                              ├── CloudFront Logs - Inventory Overview
                              └── CloudFront Logs - Events Overview
   │
   ▼  evening (saves ~$4.50/day on m6i.xlarge)
   sp el delete --all -y
```

**The `sg-send sync` redesign collapses the manual two-step into one verb**, sharing a single `Call__Counter` and emitting one unified summary. That's the architectural target for the next phase.

---

## 11. Use cases — who's actually running this

| Use case | Today's command path | Frequency | Pain point |
|----------|----------------------|-----------|------------|
| **Daily traffic refresh** | `inventory load` then `events load --from-inventory` | Daily | Two commands, two summaries, two counters → no unified view |
| **Backfill last week** | Loop the two commands across `--prefix 2026/04/{20..27}` | Ad-hoc | Manual scripting; no resume after a failure |
| **"What hit us yesterday?"** | Open Kibana dashboard, set time filter | Per investigation | Stack must be up, manifest must be fresh |
| **Single-file inspection** | `sg-send view <key> --table` | During parser/classifier debugging | Stable, works well |
| **"Did this date load?"** | `sg-send files <date>` | Ad-hoc | Read-only, no S3 — fast and cheap |
| **Bot vs human ratio over time** | Events dashboard, "Bot vs Human" panel | Reporting | Stable today |
| **Pipeline-run audit** | (no CLI yet — read `sg-pipeline-runs-*` directly in Kibana) | Post-incident | Phase B journal exists; read-side CLI does not |
| **Rebuild from scratch** | `events wipe` (resets manifest) then `inventory wipe` then re-load both | Recovery / test | Two commands again — `wipe-all` would be a Tier 3 win |

---

## 12. Ground rules that constrain the design (one-page summary)

The new orchestrator and its commands must respect every rule that's already in force. Sourced from `.claude/CLAUDE.md` and `team/comms/briefs/v0.1.72__sp-cli-fastapi-duality.md`:

| Rule | Meaning for the orchestrator |
|------|------------------------------|
| **Type_Safe everywhere** | No Pydantic, no dataclass, no plain class. Every schema in its own file. |
| **Zero raw primitives** | `str`, `int`, `dict`, `list` never appear as attributes. `Safe_*` / `Enum__*` / collection subclasses only. |
| **No Literals** | Verb is `Enum__Pipeline__Verb`, queue mode is `Safe_Str__Text` or a new enum, never a Literal. |
| **Three-tier architecture** | Pure service class (`SG_Send__Orchestrator`) — Typer wrapper has no business logic — FastAPI route deferred (consistent with `sp el` itself being CLI-only today). |
| **AWS boundaries** | All boto3 stays in `S3__Inventory__Lister` / `S3__Object__Fetcher`. No new boto3 in the orchestrator. |
| **HTTP boundary** | All ES/Kibana HTTP through `Inventory__HTTP__Client`. No `requests` calls in the orchestrator. |
| **No mocks in tests** | `*__In_Memory` subclasses for all collaborators. Pattern already established in slices 1 & 2. |
| **Matched wipe** | Any new write path needs a matched wipe — but the orchestrator only writes via slice 1 + 2, which already have wipes. So the existing wipe pair is sufficient (Tier 3 `wipe-all` is convenience only). |
| **Reality doc updates with code** | Code authors update reality in the same commit. The orchestrator PR includes the v0.1.101 reality update. |
| **Branch naming** | `claude/{description}-{session-id}`. Never push to `dev` directly. |

---

## Appendix — Files to read for the implementation session

In dependency order:

1. `sgraph_ai_service_playwright__cli/elastic/lets/Call__Counter.py` — line 15-17 has the forward declaration to honour.
2. `sgraph_ai_service_playwright__cli/elastic/lets/runs/service/Pipeline__Runs__Tracker.py` — the journal contract every loader (and the orchestrator) will use.
3. `sgraph_ai_service_playwright__cli/elastic/lets/runs/schemas/Schema__Pipeline__Run.py` — the journal record fields.
4. `sgraph_ai_service_playwright__cli/elastic/lets/cf/inventory/service/Inventory__Loader.py` — the orchestration template.
5. `sgraph_ai_service_playwright__cli/elastic/lets/cf/events/service/Events__Loader.py` — the more complex template (with `--from-inventory` + manifest update).
6. `sgraph_ai_service_playwright__cli/elastic/lets/cf/sg_send/service/SG_Send__Date__Parser.py` — date parsing already exists; reuse, don't redesign.
7. `tests/unit/sgraph_ai_service_playwright__cli/elastic/lets/cf/inventory/service/test_Inventory__Loader.py` — orchestrator test shape.
8. `tests/unit/sgraph_ai_service_playwright__cli/elastic/lets/cf/events/service/test_Events__Loader.py` — composite-orchestrator test shape (with `--from-inventory` path).
