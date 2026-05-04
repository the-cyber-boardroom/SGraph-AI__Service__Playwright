# 01 — History and Context

---

## 1. The starting point — an empty Kibana

In April 2026, the `sp el` (Ephemeral Kibana) slice shipped.  It gave us a
single command (`sp el create-from-ami --wait`, ~80 seconds) to spin up a
fresh Elasticsearch + Kibana + nginx/TLS stack on EC2, demo it, and tear it
down.  A "Synthetic Logs Overview" dashboard proved the plumbing with fake
data.  Beautiful, but empty.

Meanwhile, AWS Firehose had been writing **CloudFront real-time logs** to
S3 for weeks:

```
s3://745506449035--sgraph-send-cf-logs--eu-west-2/cloudfront-realtime/
```

~300–400 gzipped `.gz` objects per day, sub-2 KB each, completely unread.
We had zero operational visibility into site traffic.

---

## 2. The LETS framing

The user introduced the **LETS principle** as the organising architecture:

> *"Persist Everything Important BEFORE Indexing Anything.  Elasticsearch
> is NOT the source of truth — it is an index, a cache, a search layer, a
> visualisation layer."*

**L — Load:** data arrives or is retrieved from its authoritative source.  
**E — Extract:** raw bytes are decoded into typed records.  
**T — Transform:** enrichment, aggregation, derived fields (mostly deferred).  
**S — Save:** records are indexed / persisted into the queryable layer.

Key consequence: every `load` has a matched `wipe`.  Kibana holds
**disposable indexes** — rebuilding from S3 is always possible.

---

## 3. Slice 1 — `sp el lets cf inventory` (2026-04-26)

**Goal:** smallest possible end-to-end LETS pass.  Prove the data path
without touching `.gz` content.

What it does:
- `ListObjectsV2` the CloudFront-realtime S3 bucket (no `GetObject`)
- Parse Firehose-embedded timestamps out of the S3 key filenames
- Index one `Schema__S3__Object__Record` per `.gz` file into
  `sg-cf-inventory-{YYYY-MM-DD}` (daily rolling, keyed by etag)
- Auto-import a 5-panel "CloudFront Logs - Inventory Overview" Kibana
  dashboard
- `inventory load` / `wipe` / `list` / `health`

Why metadata-only on slice 1:
- Proves S3 pagination, the Elastic HTTP client, dashboard import, and the
  entire CLI scaffolding before touching binary content
- `content_processed: bool` field on each inventory doc is a **forward
  declaration** — slice 2 will use it as a manifest

Result: ~425 docs per day in ~2 seconds.  150 unit tests, zero mocks.

---

## 4. Slice 2 — `sp el lets cf events` (2026-04-26)

**Goal:** read the `.gz` content, parse the 38-field CloudFront TSV, index
real traffic events.

What it does:
- `GetObject` each `.gz` from S3, gunzip, parse TSV
- `Bot__Classifier`: 28 named-bot regex patterns + 5 generic
  word-bounded indicators → `Enum__CF__Bot__Category` (HUMAN / BOT_KNOWN /
  BOT_GENERIC / UNKNOWN)
- Indexes `Schema__CF__Event__Record` (38 fields) into
  `sg-cf-events-{YYYY-MM-DD}` (keyed by `{etag}__{line_index}` for
  per-event idempotency)
- Auto-imports a 6-panel "CloudFront Logs - Events Overview" dashboard
- After each file: flips slice 1's `inventory.content_processed = true`
  via `_update_by_query`
- **`--from-inventory` mode**: reads the manifest (inventory docs where
  `content_processed=false`) as the work queue → incremental daily refresh
- `events load` / `wipe` / `list` / `health`
- `--skip-processed`: alternative dedup strategy — queries inventory for
  already-processed etags and filters them out before building the queue

Real-world validation: 565 events from 50 `.gz` files in ~12 seconds.
201 unit tests, zero mocks.

---

## 5. Phase A — Cross-cutting diagnostics (2026-04-27)

Three new infrastructure classes added to the `lets` layer:

**`Call__Counter`** (`elastic/lets/Call__Counter.py`)  
Tracks S3 calls and Elastic HTTP calls during a single run.  Designed to be
constructed once and injected into all collaborators so the final tally
spans the whole run.  Its docstring explicitly names `SG_Send__Orchestrator`
as the future class that will do this wiring — that class does not yet
exist.

**`Step__Timings`** (`elastic/lets/Step__Timings.py`)  
Per-file timing breakdown: `s3_get_ms`, `gunzip_ms`, `parse_ms`,
`bulk_post_ms`, `manifest_update_ms`.  Used by `Progress__Reporter` to show
the operator where wall time is spent.

**`Progress__Reporter`** (`elastic/lets/cf/events/service/Progress__Reporter.py`)  
Base no-op class with hooks: `on_queue_built`, `on_skip_filter_done`,
`on_file_done`, `on_file_error`, `on_load_complete`.  The CLI provides a
Rich-backed subclass (`Console__Progress__Reporter`).

---

## 6. Phase A.5 — `sp el lets cf sg-send` diagnostic commands (2026-04-27)

A new Typer sub-app `sg_send_app` was mounted under `cf_app`, giving:

```
sp el lets cf sg-send files <date>    # query inventory index for a day/hour
sp el lets cf sg-send view <key>      # fetch one .gz, show raw TSV or --table
```

Supporting service classes:

- `SG_Send__Date__Parser` — parses `MM/DD`, `MM/DD/HH`, `YYYY/MM/DD`,
  `YYYY/MM/DD/HH` into `(year, month, day, hour|None)`; defaults year to
  2026
- `SG_Send__File__Viewer` — wraps `S3__Object__Fetcher` +
  `CF__Realtime__Log__Parser` for single-file inspection
- `SG_Send__Inventory__Query` — one Elastic query against
  `sg-cf-inventory-*` filtered by year/month/day/hour

These are **diagnostic/read-only** commands.  No writes.  The comment in
`elastic_lets.py` labels them "diagnostic commands **so far**" — more
sg-send verbs are explicitly expected.

---

## 7. Where things stand today

Everything above is **merged to `dev`** and on branch
`claude/spell-commands-observability-vO6wV`.

The `SG_Send__Orchestrator` mentioned in `Call__Counter`'s docstring does
**not exist** — it is the obvious missing piece that the next phase should
design and implement.
