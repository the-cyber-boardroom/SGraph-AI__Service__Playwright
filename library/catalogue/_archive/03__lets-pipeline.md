# 03 — LETS Pipeline

→ [Catalogue README](README.md)

The LETS pipeline indexes CloudFront real-time logs from S3 into Elasticsearch,
providing analytics via Kibana dashboards. Accessed via `sp el lets cf …` CLI verbs.

---

## Pipeline Concept

**L**oad → (E)xtract → (T)ransform → **S**ave

In practice: Firehose `.gz` files in S3 → daily ES indices → Kibana dashboards.

---

## Slice 1 — Inventory (`sp el lets cf inventory`)

**What:** S3 listing metadata only (no content reads). One doc per `.gz` file.

| Verb | Action |
|------|--------|
| `load [--prefix YYYY[/MM[/DD]]] [--all] [--max-keys N]` | List S3, index into `sg-cf-inventory-{YYYY-MM-DD}` |
| `wipe [-y]` | Delete all inventory indices + data view + dashboard |
| `list [--top N]` | Show recent run summaries |
| `health` | Cluster health probe |

**Key classes:** `S3__Inventory__Lister`, `Inventory__HTTP__Client`, `Run__Id__Generator`, `Inventory__Loader`, `Inventory__Wiper`, `CF__Inventory__Dashboard__Builder`

**Index:** `sg-cf-inventory-{YYYY-MM-DD}` — keyed by `delivery_at`, `_id = etag`

**Tests:** 150 unit tests under `tests/unit/…/elastic/lets/cf/inventory/`

Reality doc: `team/roles/librarian/reality/v0.1.31/10__lets-cf-inventory.md`

---

## Slice 2 — Events (`sp el lets cf events`)

**What:** Reads each `.gz` via `s3:GetObject`, gunzips, parses TSV (38-field schema), indexes per-event with `_id = {etag}__{line_index}`. Updates slice 1's manifest.

| Verb | Action |
|------|--------|
| `load [--from-inventory] [--max-files N]` | Fetch + parse + index events |
| `wipe [-y]` | Delete events indices + data view + dashboard + reset inventory manifest |
| `list [--top N]` | Show recent run summaries |
| `health` | Cluster health probe |

**`--from-inventory` fast path:** reads `sg-cf-inventory-*` docs where `content_processed=false` as the work queue. Flips each to `true` on success.

**Key classes:** `S3__Object__Fetcher`, `Bot__Classifier`, `CF__Realtime__Log__Parser`, `Inventory__Manifest__Reader`, `Inventory__Manifest__Updater`, `Events__Loader`, `Events__Wiper`, `CF__Events__Dashboard__Builder`

**Index:** `sg-cf-events-{YYYY-MM-DD}` — keyed by event `timestamp[:10]`

**Tests:** 201 unit tests under `tests/unit/…/elastic/lets/cf/events/`

Reality doc: `team/roles/librarian/reality/v0.1.31/11__lets-cf-events.md`

---

## Slice 3 — Consolidate (`sp el lets cf consolidate`)

**What (C-stage):** Collapses many Firehose `.gz` files for one date into a single `events.ndjson.gz` artefact in S3. Enables ~14× speedup on the events-load path.

| Verb | Action |
|------|--------|
| `load [--date YYYY-MM-DD] [--max-files N] [--dry-run]` | Build consolidated artefact in S3 |

**`events load --from-consolidated`:** reads pre-built `events.ndjson.gz` directly (one bulk-post, uses E-1 + E-2 optimisations).

**S3 layout:**
```
s3://{bucket}/lets/{compat-region}/{YYYY}/{MM}/{DD}/
    events.ndjson.gz      ← consolidated events
    manifest.json         ← run_id, counts, s3_output_key
lets/{compat-region}/lets-config.json   ← compat-region config
```

**Key classes:** `Consolidate__Loader`, `NDJSON__Writer`, `NDJSON__Reader`, `Manifest__Builder`, `S3__Object__Writer`, `Lets__Config__Writer`, `Lets__Config__Reader`

**ES indices:** `sg-cf-consolidated-{YYYY-MM-DD}` (one manifest doc per run)

**Tests:** ~57 new tests; full suite 499 passed.

Reality doc: `team/roles/librarian/reality/v0.1.31/12__lets-cf-consolidate.md`

---

## Slice 4 — SG_Send (`sp el lets cf sg-send`)

**What:** Syncs the SG_Send service with the indexed CloudFront events.

| File | Role |
|------|------|
| `sg_send/service/SG_Send__Orchestrator.py` | Orchestrator |
| `sg_send/service/SG_Send__Inventory__Query.py` | Query inventory index |
| `sg_send/service/SG_Send__Date__Parser.py` | Date parsing helper |
| `sg_send/service/SG_Send__File__Viewer.py` | Diagnostic file viewer |

Tests: `tests/unit/…/elastic/lets/cf/sg_send/`

---

## Pipeline Run Journal

Every `load()` call journals into `sg-pipeline-runs-{YYYY-MM-DD}` via `Pipeline__Runs__Tracker`.

| File | Role |
|------|------|
| `elastic/lets/runs/service/Pipeline__Runs__Tracker.py` | Writes journal entries |
| `elastic/lets/runs/enums/Enum__Pipeline__Verb.py` | Verbs: `inventory-load`, `events-load`, `consolidate-load` |
| `elastic/lets/runs/schemas/Schema__Pipeline__Run.py` | Journal doc schema |

---

## ES Index Summary

| Index pattern | Content | Keyed on |
|---------------|---------|----------|
| `sg-cf-inventory-{YYYY-MM-DD}` | S3 object metadata | `delivery_at` |
| `sg-cf-events-{YYYY-MM-DD}` | Parsed CF log events | event `timestamp` |
| `sg-cf-consolidated-{YYYY-MM-DD}` | Consolidation run manifests | `run_id` |
| `sg-pipeline-runs-{YYYY-MM-DD}` | Per-load() journal entries | `loaded_at` |

---

## Cross-Links

- `04__elastic-stack.md` — Elastic/Kibana stack that hosts these indices
- `02__cli-packages.md` — `elastic/` sub-package layout
- `06__scripts-and-cli.md` — `scripts/elastic_lets.py` Typer tree
