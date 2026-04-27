# 02 — What Exists Today

Everything described here is **verified in code on `dev`**.  If it's not
listed here, it does not exist.

---

## CLI surface — complete command tree

```
sp el lets                                    Typer app (elastic_lets.py)
sp el lets cf                                 CloudFront LETS pipelines
sp el lets cf inventory                       S3 metadata pipeline (slice 1)
sp el lets cf inventory load                  List S3 → index sg-cf-inventory-{YYYY-MM-DD}
sp el lets cf inventory wipe                  Drop indices + data view + dashboard
sp el lets cf inventory list                  Distinct pipeline_run_id values
sp el lets cf inventory health                Three plumbing checks
sp el lets cf events                          Content-reading pipeline (slice 2)
sp el lets cf events load                     Fetch .gz → parse TSV → index sg-cf-events-{YYYY-MM-DD}
sp el lets cf events wipe                     Drop indices + data view + dashboard + reset manifest
sp el lets cf events list                     Distinct pipeline_run_id values
sp el lets cf events health                   Four checks incl. inventory-link
sp el lets cf sg-send                         SGraph-Send convenience shortcuts
sp el lets cf sg-send files <date>            Query inventory for a day/hour (read-only, no S3)
sp el lets cf sg-send view <key>              Fetch one .gz; raw TSV or --table parsed events
```

---

## Key flags

| Command | Notable flags |
|---------|---------------|
| `inventory load` | `--prefix`, `--all`, `--max-keys`, `--dry-run`, `--run-id` |
| `events load` | `--prefix`, `--all`, `--max-files`, `--from-inventory`, `--skip-processed`, `--dry-run`, `--run-id` |
| `sg-send files` | `<date>` (MM/DD or YYYY/MM/DD or with hour), `--page-size` |
| `sg-send view` | `<key>`, `--table`, `--limit`, `--bucket`, `--region` |

---

## Module tree

```
sgraph_ai_service_playwright__cli/elastic/lets/
  Call__Counter.py                   Cross-run S3 + Elastic call counter
  Step__Timings.py                   Per-file timing breakdown (5 steps)
  cf/
    inventory/                       Slice 1
      enums/
        Enum__LETS__Source__Slug     "cloudfront-realtime"
        Enum__LETS__Stage            LOAD / EXTRACT / TRANSFORM / SAVE
        Enum__S3__Storage_Class      STANDARD / INTELLIGENT_TIERING / …
      primitives/
        Safe_Str__Pipeline__Run__Id
        Safe_Str__S3__Bucket
        Safe_Str__S3__ETag
        Safe_Str__S3__Key
        Safe_Str__S3__Key__Prefix
      schemas/
        Schema__S3__Object__Record   One inventory doc (38 fields incl. content_processed)
        Schema__Inventory__Load__Request
        Schema__Inventory__Load__Response
        Schema__Inventory__Run__Summary
        Schema__Inventory__Wipe__Response
      collections/
        List__Schema__S3__Object__Record
        List__Schema__Inventory__Run__Summary
      service/
        S3__Inventory__Lister        boto3 ListObjectsV2 paginator + in-memory seam
        Inventory__HTTP__Client      All Elastic HTTP calls for both slices (reused by slice 2)
        Inventory__Loader            Orchestrator for inventory load
        Inventory__Wiper             Orchestrator for inventory wipe
        Inventory__Read              list + health verbs
        Run__Id__Generator           ISO timestamp + slug + 4-char hex suffix
        CF__Inventory__Dashboard__Builder   5-panel ndjson generator
        CF__Inventory__Dashboard__Ids       Shared ID constants
    events/                          Slice 2
      enums/
        Enum__CF__Bot__Category      HUMAN / BOT_KNOWN / BOT_GENERIC / UNKNOWN
        Enum__CF__Method             GET / POST / PUT / … / OTHER
        Enum__CF__Protocol           http / https / ws / wss / other
        Enum__CF__Edge__Result__Type Hit / RefreshHit / Miss / Error / …
        Enum__CF__SSL__Protocol      TLSv1.0–1.3 + OTHER
        Enum__CF__Status__Class      1xx / 2xx / 3xx / 4xx / 5xx / other
      primitives/
        Safe_Str__CF__Country        ISO-3166 alpha-2, uppercased
        Safe_Str__CF__Edge__Location POP code e.g. "HIO52-P4"
        Safe_Str__CF__Edge__Request__Id
        Safe_Str__CF__URI__Stem      URL path, max 2048 chars
        Safe_Str__CF__User__Agent    Printable ASCII, max 500 chars
        Safe_Str__CF__Referer        Printable ASCII, max 1024
        Safe_Str__CF__Host           RFC-952/1123, lowercased
        Safe_Str__CF__Cipher         IANA cipher names, uppercased
        Safe_Str__CF__Content__Type  MIME + params, lowercased
      schemas/
        Schema__CF__Event__Record    38-field typed CloudFront event
        Schema__Events__Load__Request
        Schema__Events__Load__Response
        Schema__Events__Run__Summary
        Schema__Events__Wipe__Response
      collections/
        List__Schema__CF__Event__Record
        List__Schema__Events__Run__Summary
      service/
        S3__Object__Fetcher          boto3 GetObject boundary
        CF__Realtime__Log__Parser    TSV → records + Stage-1 derivations
        Bot__Classifier              UA → Enum__CF__Bot__Category
        Inventory__Manifest__Reader  Query inventory for content_processed=false
        Inventory__Manifest__Updater mark_processed(etag) + reset_all_processed()
        Events__Loader               Orchestrator (queue → fetch → parse → post → mark)
        Events__Wiper                4-step idempotent reset incl. manifest reset
        Events__Read                 list_runs + health (4 checks)
        CF__Events__Dashboard__Builder  6-panel ndjson generator
        CF__Events__Dashboard__Ids      Shared ID constants
        Progress__Reporter           No-op base; CLI overrides with Rich output
    sg_send/                         SGraph-Send convenience layer (Phase A.5)
      service/
        SG_Send__Date__Parser        MM/DD or YYYY/MM/DD/HH → (y, m, d, h)
        SG_Send__File__Viewer        raw_text(key) + parsed(key) for one .gz
        SG_Send__Inventory__Query    ES query on sg-cf-inventory-* by date

scripts/
  elastic_lets.py                    All Typer CLI commands (915 lines)
  elastic.py                         Parent — mounts lets_app via add_typer
```

---

## Elastic indices and Kibana objects

| Index / object | Created by | Removed by |
|----------------|-----------|------------|
| `sg-cf-inventory-{YYYY-MM-DD}` | `inventory load` | `inventory wipe` |
| data view `sg-cf-inventory-*` | `inventory load` | `inventory wipe` |
| dashboard `sg-cf-inventory-overview` + 5 viz | `inventory load` | `inventory wipe` |
| `sg-cf-events-{YYYY-MM-DD}` | `events load` | `events wipe` |
| data view `sg-cf-events-*` | `events load` | `events wipe` |
| dashboard `sg-cf-events-overview` + 6 viz | `events load` | `events wipe` |

`events wipe` also resets `content_processed=false` on all inventory docs
(the manifest link between slices 1 and 2).

---

## Data flow

```
S3  cloudfront-realtime/{YYYY}/{MM}/{DD}/{HH}/EXXXX.{date}.{id}.gz
     │
     │  slice 1 — ListObjectsV2 (no GetObject)
     ▼
sg-cf-inventory-{YYYY-MM-DD}
     │  Schema__S3__Object__Record
     │  _id = etag   content_processed: false → true (after slice 2)
     │
     │  slice 2 — GetObject + gzip.decompress + TSV parse
     ▼
sg-cf-events-{YYYY-MM-DD}
     │  Schema__CF__Event__Record (38 fields)
     │  _id = {etag}__{line_index}
     ▼
Kibana dashboards (both auto-imported, both disposable)
```

---

## Default bucket

```
745506449035--sgraph-send-cf-logs--eu-west-2
```

All `sg-send` commands assume this bucket.  Other commands take `--bucket`.

---

## Test counts

| Area | Tests |
|------|-------|
| Slice 1 (inventory) | ~150 unit tests |
| Slice 2 (events) | ~201 unit tests |
| sg-send + Call__Counter | ~15 unit tests |
| **Total** | **~366 tests, zero mocks** |

All tests use in-memory collaborator subclasses (`*__In_Memory`) or
canned fixtures — no boto3, no real Elastic.

---

## Key design rules (non-negotiable)

1. **One class per file** — every schema, enum, primitive, collection in
   its own `.py` file named exactly after the class.
2. **All classes extend `Type_Safe`** — no plain Python classes.
3. **No Pydantic, no Literals** — fixed-value sets use `Enum__*` classes.
4. **Routes have no logic** — pure delegation (not relevant here since
   `lets` is CLI-only, but the rule flows through).
5. **No mocks in tests** — use `*__In_Memory` subclasses.
6. **`═══` 80-char file headers** — every file.
7. **Inline comments only** — no docstrings.
8. **`__init__.py` stays empty** — no re-exports.
