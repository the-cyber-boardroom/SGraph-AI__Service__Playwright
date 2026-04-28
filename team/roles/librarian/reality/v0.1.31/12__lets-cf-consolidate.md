# 12 — LETS CF Consolidate (C-stage)

**Added:** 2026-04-28  
**Slice:** v0.1.100 (consolidation slice — `claude/review-consolidation-strategy-Cp8v7`)

---

## What Exists

The C-stage consolidation pipeline ships alongside the inventory (slice 1) and events (slice 2) stages. It collapses many small Firehose `.gz` files for a single date into one `events.ndjson.gz` artefact, enabling a ~14× speedup on the events-load path.

---

## New Module Tree

```
sgraph_ai_service_playwright__cli/elastic/lets/cf/consolidate/
    __init__.py
    enums/
        Enum__Lets__Workflow__Type.py     (CONSOLIDATE / COMPRESS / EXPAND / UNKNOWN)
    primitives/
        __init__.py                       (no concrete primitives yet — folder reserved)
    schemas/
        Schema__Consolidate__Load__Request.py
        Schema__Consolidate__Load__Response.py
        Schema__Consolidated__Manifest.py
        Schema__Lets__Config.py
    collections/
        List__Schema__Consolidated__Manifest.py
    service/
        S3__Object__Writer.py             (boto3 s3:PutObject boundary)
        NDJSON__Writer.py                 (List__Schema__CF__Event__Record → gzip NDJSON bytes)
        NDJSON__Reader.py                 (gzip NDJSON bytes → List__Schema__CF__Event__Record)
        Manifest__Builder.py              (assembles Schema__Consolidated__Manifest)
        Lets__Config__Writer.py           (Schema__Lets__Config → JSON bytes)
        Lets__Config__Reader.py           (JSON bytes → Schema__Lets__Config + compat check)
        Consolidate__Loader.py            (orchestrator — the C-stage entry point)
```

---

## Modified Existing Files (additive only)

| File | Change |
|------|--------|
| `Enum__Pipeline__Verb` | `CONSOLIDATE_LOAD = 'consolidate-load'` added |
| `Schema__S3__Object__Record` | `consolidation_run_id` + `consolidated_at` fields added (empty default — backward-compat) |
| `Schema__Events__Load__Request` | `from_consolidated`, `date_iso`, `compat_region` fields added |
| `Events__Loader` | `ndjson_reader`, `config_reader` collaborators + `_load_from_consolidated()` method |
| `Inventory__HTTP__Client` | 7 ES optimisations (E-1 to E-7): refresh param, routing param, session keep-alive, `ensure_index_template`, auto-split by bytes, `update_by_query_terms`, explicit `trigger_refresh` |
| `scripts/elastic_lets.py` | `consolidate_app` Typer sub-tree + `cmd_consolidate_load` + `build_consolidate_loader()` |

---

## S3 Layout

```
s3://{bucket}/lets/{compat_region}/
    lets-config.json                    ← compat-region config (written on first use)
    {YYYY}/{MM}/{DD}/
        events.ndjson.gz                ← consolidated events for the date
        manifest.json                   ← per-run sidecar (run_id, counts, s3_output_key)
```

Default compat region: `raw-cf-to-consolidated`

---

## CLI Verbs

```
sp el lets cf consolidate load [stack] [options]
    --date YYYY-MM-DD      date to consolidate (default: today UTC)
    --bucket               S3 bucket (default: SGraph CloudFront-logs bucket)
    --compat-region        region subfolder (default: raw-cf-to-consolidated)
    --max-files N          stop after N source files (default: all)
    --run-id               explicit run id (default: auto-generated)
    --password             Elastic password (else $SG_ELASTIC_PASSWORD)
    --region               AWS region (else boto3 default chain)
    --dry-run              build queue, skip all writes

sp el lets cf events load ... --from-consolidated --date YYYY-MM-DD
    # Reads pre-built events.ndjson.gz instead of per-file fetch + parse.
    # Uses refresh=False + routing=date (E-1, E-2) for one bulk-post call.
```

---

## Elastic Indices

| Index pattern | Content |
|---------------|---------|
| `sg-cf-consolidated-{YYYY-MM-DD}` | One manifest doc per consolidation run; `_id = run_id` |
| `sg-pipeline-runs-{YYYY-MM-DD}` | One journal entry per load() call; verb = `consolidate-load` |

---

## Test Coverage

```
tests/unit/.../consolidate/enums/
    test_Enum__Lets__Workflow__Type.py
tests/unit/.../consolidate/schemas/
    test_Schema__Consolidate__Load__Request.py
    test_Schema__Consolidate__Load__Response.py
    test_Schema__Consolidated__Manifest.py
    test_Schema__Lets__Config.py
tests/unit/.../consolidate/service/
    test_NDJSON__Writer__Reader.py          (30 cases — round-trip, gzip, tolerance)
    test_Manifest__Builder.py               (8 cases)
    test_Lets__Config__Writer__Reader.py    (13 cases — write, read, compat checks)
    test_Consolidate__Loader.py             (16 cases — happy path, dry_run, errors, ES, config)
tests/unit/.../events/service/
    test_Events__Loader__from_consolidated.py  (11 cases — fast path, error handling)
```

Total new tests: **~57** (on top of 442 pre-existing). Full suite: **499 passed**.

---

## ES Optimisations Shipped

| ID | Change | Default (backward-compat) |
|----|--------|--------------------------|
| E-1 | `refresh` param on `bulk_post_with_id` | `True` |
| E-2 | `routing` param on `bulk_post_with_id` | `''` |
| E-3 | `requests.Session()` keep-alive | On by default |
| E-4 | `ensure_index_template()` method | N/A — new method |
| E-5 | Auto-split bulk payloads by `max_bytes` | `0` (disabled) |
| E-6 | `update_by_query_terms()` batch update | N/A — new method |
| E-7 | `wait_for_active_shards` param | `'null'` (ES default) |

---

## Decisions Implemented

- **Decision #5**: One `events.ndjson.gz` per day + `manifest.json` sidecar under `lets/{compat-region}/{YYYY/MM/DD}/`
- **Decision #5b**: `Lets__Config__Reader.check_compat()` validates parser/schema version before reading artefacts
- **Decision #5c**: Run-specific data in `manifest.json`, compat metadata in `lets-config.json`
- **Decision #6**: Manifest also indexed as ES doc in `sg-cf-consolidated-{date}`
- **Decision #7**: `consolidation_run_id` + `consolidated_at` fields added to `Schema__S3__Object__Record`
- **Decision #8**: `Events__Loader --from-consolidated` reads pre-built artefact (one bulk-post, E-1 + E-2)
- **Decision #11**: `S3__Object__Writer` is the ONLY new boto3 boundary; `put_object_bytes()` is the sole public method
