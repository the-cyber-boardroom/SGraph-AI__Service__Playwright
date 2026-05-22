# lets — Reality Index

**Domain:** `lets/` | **Last updated:** 2026-05-17 | **Maintained by:** Librarian
**Code-source basis:** consolidated from `_archive/v0.1.31/10,11,12__lets-cf-*.md`.

The Log Event Tracking System (LETS) pipeline for CloudFront real-time logs. Three slices layered on top of the v0.1.46 Ephemeral Kibana stack (`sp el`):

- **Slice 1 (10)** — Inventory: listing-metadata only, no `.gz` reads.
- **Slice 2 (11)** — Events: TSV parse + bot classification + per-event indexing with `_id = {etag}__{idx}`.
- **Slice 3 (12)** — Consolidate: collapse many small `.gz` files into one `events.ndjson.gz` per date, plus 7 ES optimisations (E-1..E-7).

**Canonical package:** `sgraph_ai_service_playwright__cli/elastic/lets/cf/{inventory,events,consolidate}/`.

---

## EXISTS (code-verified)

### CLI surface — under `sp el`

```
sp el lets cf inventory load   [--prefix YYYY[/MM[/DD]]] [--all] [--max-keys N]
                                [--run-id ID] [--bucket B] [--password P]
                                [--region R] [--dry-run]
sp el lets cf inventory wipe   [-y] [--password P] [--region R]
sp el lets cf inventory list   [--top N] [--password P] [--region R]
sp el lets cf inventory health [--password P] [--region R]

sp el lets cf events load      [--prefix YYYY[/MM[/DD]]] [--all] [--max-files N]
                                [--from-inventory] [--from-consolidated] [--date YYYY-MM-DD]
                                [--run-id ID] [--bucket B]
                                [--password P] [--region R] [--dry-run]
sp el lets cf events wipe      [-y] [--password P] [--region R]
sp el lets cf events list      [--top N] [--password P] [--region R]
sp el lets cf events health    [--password P] [--region R]

sp el lets cf consolidate load [stack] [options]
    --date YYYY-MM-DD          # default: today UTC
    --bucket                   # default: SGraph CloudFront-logs bucket
    --compat-region            # default: raw-cf-to-consolidated
    --max-files N              # default: all
    --run-id                   # default: auto-generated
    --password                 # else $SG_ELASTIC_PASSWORD
    --region                   # else boto3 default chain
    --dry-run                  # build queue, skip all writes

sp el lets cf iam show | plan        # desired sg-lets-cf least-priv policy; diff vs live role
sp el lets cf iam create | update    # provision/refresh the role (gated: SG_AWS__IAM__ALLOW_MUTATIONS=1 + confirm)
sp el lets cf iam test               # assume sg-lets-cf and print the caller identity (proves assumable)
sp el lets cf iam delete [-y]        # delete the role (gated)
```

All verbs accept an optional positional `[STACK_NAME]` — auto-pick when a single stack exists; prompt on multiple.

`--from-inventory` (events): pulls work queue from `sg-cf-inventory-*` docs where `content_processed=false` — slice 1's forward-declared field finally has a reader.

`--from-consolidated` (events): reads the pre-built `events.ndjson.gz` for the date instead of per-file fetch + parse. Uses `refresh=False + routing=date` (E-1, E-2) for one bulk-post call. ~14× speedup.

#### v0.2.40 — auth guard + transparent assume (`iam` sub-app)

The S3-touching cf commands (native `sync`/`cache`; TUI `traffic`/`files`/`inspect`/`architecture`/`sync`) are wrapped with `@aws_auth_guard('el-lets-cf')`:

- **Transparent assume (default):** each command assumes the scoped `sg-lets-cf` role from the operator's base identity, with a one-line stderr notice. Falls back to the base identity, then the auth menu, if the role is absent or assume is denied.
- **Auth guard:** a missing/expired credential no longer dumps a botocore traceback — interactive terminals get a menu (pick a stored keyring credential, retry in-process); piped/CI get remediation + exit 2.
- **`iam` sub-app** (`elastic/lets/cf/iam/`): `cf_role_profile.py` declares the least-priv policy and self-registers into the generic registry; `cli/Cli__CF__Iam.py` exposes show/plan/create/update/test/delete over the generic `AWS__Role__Provisioner`.

Full engine + caveats: [`cli/aws-auth.md`](../cli/aws-auth.md).

---

### Slice 1 — Inventory pipeline (`elastic/lets/cf/inventory/`)

| Layer | Files |
|-------|-------|
| **enums** (3) | `Enum__S3__Storage_Class`, `Enum__LETS__Source__Slug`, `Enum__LETS__Stage` |
| **primitives** (5) | `Safe_Str__S3__Bucket`, `Safe_Str__S3__Key`, `Safe_Str__S3__Key__Prefix`, `Safe_Str__S3__ETag`, `Safe_Str__Pipeline__Run__Id` |
| **schemas** (5) | `Schema__S3__Object__Record` (the indexed doc), `Schema__Inventory__Load__Request`, `Schema__Inventory__Load__Response`, `Schema__Inventory__Wipe__Response`, `Schema__Inventory__Run__Summary` |
| **collections** (2) | `List__Schema__S3__Object__Record`, `List__Schema__Inventory__Run__Summary` |
| **service** (7) | `S3__Inventory__Lister` (boto3 boundary), `Inventory__HTTP__Client` (sibling HTTP boundary — ES bulk + delete + count + aggregate), `Run__Id__Generator`, `Inventory__Loader`, `Inventory__Wiper`, `Inventory__Read`, `CF__Inventory__Dashboard__Builder`, `CF__Inventory__Dashboard__Ids` |

#### Load pipeline (slice 1)

1. Resolve stack via `Elastic__Service.get_stack_info()` — gets `kibana_url`.
2. List S3 via `boto3.s3.list_objects_v2` paginator — defaults to today UTC's prefix `cloudfront-realtime/{YYYY}/{MM}/{DD}/`.
3. Parse each object's filename for the Firehose-embedded timestamp `(YYYY-MM-DD-HH-MM-SS-{uuid}.gz)`.
4. Build a `Schema__S3__Object__Record` per object — bucket, key, last_modified, size_bytes, storage_class, etag (quotes stripped), source slug, derived `delivery_{year/month/day/hour/minute}`, derived `delivery_at` ISO, `firehose_lag_ms`, `pipeline_run_id`, `loaded_at`, `content_processed: false` (slice-2 hook).
5. Ensure Kibana data view `sg-cf-inventory-*` (idempotent — `Kibana__Saved_Objects__Client.ensure_data_view` reused from synthetic seed).
6. Build & import the dashboard ndjson via `CF__Inventory__Dashboard__Builder` — `overwrite=true`, idempotent.
7. Group records by `delivery_at[:10]` and bulk-post each group to its dated index `sg-cf-inventory-{YYYY-MM-DD}` with `_id = etag` so re-loads dedupe at index time.

In-memory pipeline only — no LETS `/raw/` or `/extract/` writes to disk in slice 1. The S3 bucket is the persisted Load layer.

#### Wipe (slice 1) — idempotent matched pair

1. Delete every `sg-cf-inventory-*` index via list-then-delete-by-name (wildcard DELETE blocked by ES default `action.destructive_requires_name=true`).
2. Delete both data view titles — current `sg-cf-inventory-*` and legacy pre-fix `sg-cf-inventory` (defensive).
3. Delete dashboard saved-object `sg-cf-inventory-overview` + the 5 visualisations (deterministic ids from `CF__Inventory__Dashboard__Ids`).

#### Indices / data view / dashboard (slice 1)

| Artifact | Name |
|----------|------|
| Index | `sg-cf-inventory-{YYYY-MM-DD}` (daily rolling, keyed on `delivery_at`) |
| Data view | `sg-cf-inventory-*` (wildcard, time field `delivery_at`) |
| Dashboard | `CloudFront Logs - Inventory Overview` (id `sg-cf-inventory-overview`) |
| Visualisations (5) | `sg-cf-inv-vis-{count-over-time, bytes-over-time, size-distribution, storage-class-breakdown, top-hourly-partitions}` |

Legacy Vis Editor (`visualization` saved-object type) — Lens deliberately avoided for the auto-imported path due to migration footguns documented in the v0.1.46 sp-elastic-kibana debrief.

Slice 1 tests: **150 unit tests** under `tests/unit/sgraph_ai_service_playwright__cli/elastic/lets/cf/inventory/`. Zero mocks — every collaborator has an `*__In_Memory` subclass.

---

### Slice 2 — Events pipeline (`elastic/lets/cf/events/`)

| Layer | Files |
|-------|-------|
| **enums** (6) | `Enum__CF__Method`, `Enum__CF__Protocol`, `Enum__CF__Edge__Result__Type`, `Enum__CF__SSL__Protocol`, `Enum__CF__Status__Class`, `Enum__CF__Bot__Category` |
| **primitives** (9) | `Safe_Str__CF__Country`, `Safe_Str__CF__Edge__Location`, `Safe_Str__CF__Edge__Request__Id`, `Safe_Str__CF__URI__Stem`, `Safe_Str__CF__User__Agent`, `Safe_Str__CF__Referer`, `Safe_Str__CF__Host`, `Safe_Str__CF__Cipher`, `Safe_Str__CF__Content__Type` |
| **schemas** (5) | `Schema__CF__Event__Record` (38 fields = 26 TSV + 4 derived + 5 lineage incl. `doc_id` + 3 pipeline metadata), `Schema__Events__Load__Request`, `Schema__Events__Load__Response`, `Schema__Events__Wipe__Response`, `Schema__Events__Run__Summary` |
| **collections** (2) | `List__Schema__CF__Event__Record`, `List__Schema__Events__Run__Summary` |
| **service** (10) | `S3__Object__Fetcher` (boto3 boundary for GetObject), `Bot__Classifier` (UA → category), `CF__Realtime__Log__Parser` (TSV → records + Stage 1 derivations), `Inventory__Manifest__Reader`, `Inventory__Manifest__Updater` (`mark_processed` + `reset_all_processed`), `Events__Loader`, `Events__Wiper`, `Events__Read`, `CF__Events__Dashboard__Builder`, `CF__Events__Dashboard__Ids` |

#### Load pipeline (slice 2)

1. Resolve stack.
2. Build queue — two modes: **S3-listing** (default; via slice 1's `S3__Inventory__Lister`) or **`--from-inventory`** (query `sg-cf-inventory-*` for `content_processed=false`, sorted by `delivery_at` desc).
3. Ensure Kibana data view `sg-cf-events-*`.
4. Build & import dashboard ndjson (idempotent).
5. Per file: `s3:GetObject` → bytes → `gzip.decompress` → `CF__Realtime__Log__Parser.parse()` (TSV split + URL-decode UA + trim referer + bot classify + status class derive + cache_hit flag — single pass) → stamp `source_bucket/key/etag`, `line_index`, `doc_id = {etag}__{idx}`, `pipeline_run_id`, `loaded_at` → group by `timestamp[:10]` → bulk-post per-day with `id_field='doc_id'` for per-event idempotency → on success `Inventory__Manifest__Updater.mark_processed(etag, run_id)`.

#### Wipe (slice 2) — 4-step idempotent reset

1. Delete every `sg-cf-events-*` index (per-name, not wildcard — slice 1's bug-fix lesson).
2. Delete data view `sg-cf-events-*`.
3. Delete dashboard `sg-cf-events-overview` + 6 visualisations.
4. Reset inventory manifest — `_update_by_query` flips every `content_processed=true` back to false.

#### Indices / data view / dashboard (slice 2)

| Artifact | Name |
|----------|------|
| Index | `sg-cf-events-{YYYY-MM-DD}` (daily rolling, keyed on each event's `timestamp[:10]`) |
| Data view | `sg-cf-events-*` (wildcard, time field `timestamp`) |
| Dashboard | `CloudFront Logs - Events Overview` (id `sg-cf-events-overview`) |
| Visualisations (6) | `sg-cf-evt-vis-{status-over-time, edge-result, top-uris, geographic, latency-percentiles, bot-vs-human}` |

Slice 2 tests: **201 unit tests** under `tests/unit/sgraph_ai_service_playwright__cli/elastic/lets/cf/events/`. Zero mocks. Real CF log lines (`/enhancecp` and `/robots.txt` from wpbot bot) live as golden fixtures in `test_CF__Realtime__Log__Parser.py`.

---

### Slice 3 — Consolidate pipeline (`elastic/lets/cf/consolidate/`)

C-stage consolidation pipeline collapsing many small Firehose `.gz` files for a single date into one `events.ndjson.gz` artefact. ~14× speedup on the events-load path.

```
sgraph_ai_service_playwright__cli/elastic/lets/cf/consolidate/
    enums/Enum__Lets__Workflow__Type.py     (CONSOLIDATE / COMPRESS / EXPAND / UNKNOWN)
    schemas/{Schema__Consolidate__Load__Request, ..__Response,
             Schema__Consolidated__Manifest, Schema__Lets__Config}
    collections/List__Schema__Consolidated__Manifest
    service/
        S3__Object__Writer.py     (boto3 s3:PutObject boundary)
        NDJSON__Writer.py         (records → gzip NDJSON bytes)
        NDJSON__Reader.py         (gzip NDJSON bytes → records)
        Manifest__Builder.py
        Lets__Config__Writer.py   (Schema__Lets__Config → JSON bytes)
        Lets__Config__Reader.py   (JSON bytes → Schema__Lets__Config + compat check)
        Consolidate__Loader.py    (orchestrator — the C-stage entry point)
```

#### Modified existing files (additive only)

| File | Change |
|------|--------|
| `Enum__Pipeline__Verb` | `CONSOLIDATE_LOAD = 'consolidate-load'` added |
| `Schema__S3__Object__Record` | `consolidation_run_id` + `consolidated_at` fields added (empty default) |
| `Schema__Events__Load__Request` | `from_consolidated`, `date_iso`, `compat_region` fields added |
| `Events__Loader` | `ndjson_reader`, `config_reader` collaborators + `_load_from_consolidated()` method |
| `Inventory__HTTP__Client` | 7 ES optimisations (E-1..E-7) |
| `scripts/elastic_lets.py` | `consolidate_app` Typer sub-tree + `cmd_consolidate_load` |

#### S3 layout

```
s3://{bucket}/lets/{compat_region}/
    lets-config.json                    ← compat-region config (written on first use)
    {YYYY}/{MM}/{DD}/
        events.ndjson.gz                ← consolidated events for the date
        manifest.json                   ← per-run sidecar
```

Default compat region: `raw-cf-to-consolidated`.

#### Elastic indices

| Index pattern | Content |
|---------------|---------|
| `sg-cf-consolidated-{YYYY-MM-DD}` | One manifest doc per consolidation run; `_id = run_id` |
| `sg-pipeline-runs-{YYYY-MM-DD}` | One journal entry per `load()` call; verb = `consolidate-load` |

#### ES optimisations shipped

| ID | Change | Default |
|----|--------|---------|
| E-1 | `refresh` param on `bulk_post_with_id` | `True` |
| E-2 | `routing` param on `bulk_post_with_id` | `''` |
| E-3 | `requests.Session()` keep-alive | On by default |
| E-4 | `ensure_index_template()` method | N/A — new method |
| E-5 | Auto-split bulk payloads by `max_bytes` | `0` (disabled) |
| E-6 | `update_by_query_terms()` batch update | N/A — new method |
| E-7 | `wait_for_active_shards` param | `'null'` (ES default) |

Slice 3 tests: ~57 new (`tests/unit/.../consolidate/...` + `tests/unit/.../events/service/test_Events__Loader__from_consolidated.py`). Full suite: **499 passing**.

---

### Decisions implemented (slice 3)

- **#5** — One `events.ndjson.gz` per day + `manifest.json` sidecar under `lets/{compat-region}/{YYYY/MM/DD}/`.
- **#5b** — `Lets__Config__Reader.check_compat()` validates parser/schema version before reading.
- **#5c** — Run-specific data in `manifest.json`; compat metadata in `lets-config.json`.
- **#6** — Manifest also indexed as ES doc in `sg-cf-consolidated-{date}`.
- **#7** — `consolidation_run_id` + `consolidated_at` fields added to `Schema__S3__Object__Record`.
- **#8** — `Events__Loader --from-consolidated` reads pre-built artefact (one bulk-post, E-1 + E-2).
- **#11** — `S3__Object__Writer` is the ONLY new boto3 boundary; `put_object_bytes()` is the sole public method.

---

## PROPOSED — does not exist yet

See [`proposed/index.md`](proposed/index.md).

---

## See also

- Sources: [`_archive/v0.1.31/10__lets-cf-inventory.md`](../_archive/v0.1.31/10__lets-cf-inventory.md), [`11__lets-cf-events.md`](../_archive/v0.1.31/11__lets-cf-events.md), [`12__lets-cf-consolidate.md`](../_archive/v0.1.31/12__lets-cf-consolidate.md)
- CLI mount: [`cli/duality.md`](../cli/duality.md) — `scripts/elastic_lets.py` mounted on `sp el`
- Stack target: the `sp el` Elastic stack — see [`cli/duality.md`](../cli/duality.md) Phase B section
