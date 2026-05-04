# 03 — Schemas and module layout

Per CLAUDE.md rule 21 ("one class per file") and rule 22 ("__init__.py stays
empty"), every schema below lives in its own `.py` file under the per-class
folder structure.

New top-level subpackage: `sgraph_ai_service_playwright__cli/elastic/lets/`.
First and only use case in this slice: `cf/inventory/`.

---

## Module tree

```
sgraph_ai_service_playwright__cli/elastic/lets/
  __init__.py                                # empty
  cf/
    __init__.py                              # empty
    inventory/
      __init__.py                            # empty
      enums/
        __init__.py
        Enum__S3__Storage_Class.py           # STANDARD / STANDARD_IA / GLACIER / ...
        Enum__LETS__Source__Slug.py          # CF_REALTIME (only one for now)
        Enum__LETS__Stage.py                 # LOAD / EXTRACT / TRANSFORM / SAVE / INDEX
      primitives/
        __init__.py
        Safe_Str__S3__Bucket.py
        Safe_Str__S3__Key.py
        Safe_Str__S3__ETag.py
        Safe_Str__Pipeline__Run__Id.py       # pattern: {iso8601}-{slug}-{shortsha}
      schemas/
        __init__.py
        Schema__S3__Object__Record.py        # the indexed doc
        Schema__Inventory__Load__Request.py
        Schema__Inventory__Load__Response.py
        Schema__Inventory__Wipe__Response.py
        Schema__Inventory__Run__Summary.py   # what `list` / `show` returns
        Schema__Inventory__Health__Response.py
      collections/
        __init__.py
        List__Schema__S3__Object__Record.py
        List__Schema__Inventory__Run__Summary.py
      service/
        __init__.py
        S3__Inventory__Lister.py             # boto3 boundary; in-memory subclass for tests
        Inventory__Loader.py                 # orchestrator: list → parse → bulk-post
        Inventory__Wiper.py                  # delete index/data view/dashboard
        Inventory__Read.py                   # backs `list` / `show` / `health`
        CF__Inventory__Dashboard__Builder.py # produces the dashboard ndjson
```

---

## Schema__S3__Object__Record (the indexed doc)

Pure-data class.  Every field is Type_Safe; no raw primitives.

```
class Schema__S3__Object__Record(Type_Safe):

    # ─── direct from S3 ListObjectsV2 ────────────────────────────────────
    bucket           : Safe_Str__S3__Bucket
    key              : Safe_Str__S3__Key
    last_modified    : Timestamp_Now                  # parsed to ISO-8601 UTC
    size_bytes       : Safe_Int__S3__Object__Size
    etag             : Safe_Str__S3__ETag             # also used as Elastic _id
    storage_class    : Enum__S3__Storage_Class

    # ─── derived from key path / filename ────────────────────────────────
    source           : Enum__LETS__Source__Slug       # CF_REALTIME
    delivery_year    : Safe_Int__Year
    delivery_month   : Safe_Int__Month
    delivery_day     : Safe_Int__Day
    delivery_hour    : Safe_Int__Hour
    delivery_minute  : Safe_Int__Minute
    delivery_at      : Timestamp_Now                  # combined ISO-8601 UTC
    firehose_lag_ms  : Safe_Int__Duration__Ms         # last_modified - delivery_at

    # ─── pipeline metadata (LETS §14) ────────────────────────────────────
    pipeline_run_id  : Safe_Str__Pipeline__Run__Id
    loaded_at        : Timestamp_Now
    schema_version   : Safe_Str__Version              # "Schema__S3__Object__Record/v1"

    # ─── content-pass forward declaration ────────────────────────────────
    content_processed       : bool                    # default False in slice 1
    content_extract_run_id  : Safe_Str__Pipeline__Run__Id   # empty string in slice 1
```

The `content_processed` field is the slice 2 hook.  Slice 2 will fetch
`.gz` files whose docs have `content_processed=false`, parse them, index the
events, and update the inventory doc to `content_processed=true` with the
run-id of the extract pass.

---

## Request / response schemas

```
class Schema__Inventory__Load__Request(Type_Safe):
    prefix           : Safe_Str__S3__Key__Prefix      # default: "" → today
    all              : bool                           # explicit full-bucket scan
    max_keys         : Safe_Int__Positive             # 0 = unlimited
    run_id           : Safe_Str__Pipeline__Run__Id    # empty → auto-generate
    stack_name       : Safe_Str__Elastic__Stack__Name # empty → auto-pick
    dry_run          : bool


class Schema__Inventory__Load__Response(Type_Safe):
    run_id           : Safe_Str__Pipeline__Run__Id
    stack_name       : Safe_Str__Elastic__Stack__Name
    prefix_resolved  : Safe_Str__S3__Key__Prefix
    pages_listed     : Safe_Int__Positive
    objects_scanned  : Safe_Int__Positive
    objects_indexed  : Safe_Int__Positive             # may be < scanned if dry_run
    objects_updated  : Safe_Int__Positive             # etag-id overwrites
    bytes_total      : Safe_Int__Positive
    started_at       : Timestamp_Now
    finished_at      : Timestamp_Now
    duration_ms      : Safe_Int__Duration__Ms
    last_http_status : Safe_Int__HTTP__Status
    kibana_url       : Safe_Str__URL


class Schema__Inventory__Wipe__Response(Type_Safe):
    stack_name           : Safe_Str__Elastic__Stack__Name
    indices_dropped      : Safe_Int__Positive
    data_views_dropped   : Safe_Int__Positive
    saved_objects_dropped: Safe_Int__Positive
    duration_ms          : Safe_Int__Duration__Ms
```

---

## Service-class responsibilities

| Class | Owns | Touches |
|-------|------|---------|
| `S3__Inventory__Lister` | `boto3.client('s3').list_objects_v2` paginator | boto3 — sole S3 boundary |
| `Inventory__Loader` | Orchestrates list → parse → bulk-post | `S3__Inventory__Lister`, existing `Elastic__HTTP__Client`, existing `Kibana__Saved_Objects__Client` |
| `Inventory__Wiper` | Deletes indices + Kibana saved-objects | existing `Elastic__HTTP__Client`, existing `Kibana__Saved_Objects__Client` |
| `Inventory__Read` | Backs `list` / `show` / `health` | existing `Elastic__HTTP__Client`, existing `Kibana__Saved_Objects__Client` |
| `CF__Inventory__Dashboard__Builder` | Produces the dashboard ndjson programmatically | None — pure data |

`Elastic__AWS__Client` is unchanged.  S3 listing is its own boundary
(`S3__Inventory__Lister`) because the existing client's scope is EC2 / IAM /
SSM lifecycle, not data plane.

---

## Test seams

Per CLAUDE.md "no mocks, no patches" rule, every external boundary gets an
in-memory subclass:

- `S3__Inventory__Lister__In_Memory` — returns canned `ListObjectsV2`
  responses without touching boto3
- existing `Elastic__HTTP__Client__In_Memory` — already used by the synthetic
  seed tests; reused unchanged
- existing `Kibana__Saved_Objects__Client__In_Memory` — same

Tests in `tests/unit/sgraph_ai_service_playwright__cli/elastic/lets/cf/inventory/`
mirror the service shape one `test_*.py` per service method.
