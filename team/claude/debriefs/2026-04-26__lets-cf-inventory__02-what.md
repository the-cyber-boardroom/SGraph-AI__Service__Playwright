# 2026-04-26 — `sp el lets cf inventory` (LETS slice 1) — 2 / 3 — What we built

This is part two of a three-part debrief on the first LETS slice.

| Part | File |
|------|------|
| 1 — Why we built this | `2026-04-26__lets-cf-inventory__01-why.md` |
| 2 — **What we built** *(this doc)* | `2026-04-26__lets-cf-inventory__02-what.md` |
| 3 — How to use it | `2026-04-26__lets-cf-inventory__03-how-to-use.md` |

---

## CLI surface

`sp el lets cf inventory ...` — four verbs, all nested under the existing
`sp el` app.

### Lifecycle (load + wipe — matched pair)

| Command | What it does |
|---|---|
| `sp el lets cf inventory load [--prefix Y[/M[/D]]] [--all] [--max-keys N] [--dry-run] [--run-id ID] [--bucket B] [--password P] [--region R]` | List S3 metadata → parse → ensure data view + dashboard → bulk-post to `sg-cf-inventory-{delivery-date}` indices with `_id = etag` |
| `sp el lets cf inventory wipe [-y] [--password P] [--region R]` | Delete every `sg-cf-inventory-*` index (per-name, not wildcard); delete both data view titles (current `sg-cf-inventory-*` and legacy `sg-cf-inventory`); delete the auto-generated dashboard's saved-objects |

### Read-only

| Command | What it does |
|---|---|
| `sp el lets cf inventory list [--top N]` | Distinct `pipeline_run_id` values currently indexed, with object count, byte sum, delivery range, latest loaded-at |
| `sp el lets cf inventory health` | Three checks: (1) at least one `sg-cf-inventory-*` index exists; (2) data view `sg-cf-inventory-*` exists; (3) dashboard `sg-cf-inventory-overview` exists.  WARN doesn't flip the rollup; only FAIL does. |

`show --run-id` was deliberately scoped out — the same query is one filter
in Kibana Discover.

---

## Architecture

### Module tree

```
sgraph_ai_service_playwright__cli/elastic/lets/cf/inventory/
  enums/
    Enum__S3__Storage_Class                STANDARD / STANDARD_IA / GLACIER / ... / UNKNOWN
    Enum__LETS__Source__Slug               CF_REALTIME (only one for now) + UNKNOWN
    Enum__LETS__Stage                      LOAD / EXTRACT / TRANSFORM / SAVE / INDEX
  primitives/
    Safe_Str__S3__Bucket                   3-63 chars, allows the SGraph "{account}--{name}--{region}" double-hyphen pattern
    Safe_Str__S3__Key                      ASCII-safe subset, 1-1024 chars
    Safe_Str__S3__Key__Prefix              same chars, allow_empty (means "full bucket")
    Safe_Str__S3__ETag                     32-hex md5 with optional "-N" multipart suffix; strips AWS's surrounding quotes
    Safe_Str__Pipeline__Run__Id            generic ASCII-id shape; format enforced by the service-side generator
  schemas/
    Schema__S3__Object__Record             19 fields: 6 from S3 listing + 8 derived from filename + 5 pipeline metadata + 2 slice-2 hooks
    Schema__Inventory__Load__Request       bucket / prefix / all / max_keys / run_id / stack_name / region / dry_run
    Schema__Inventory__Load__Response      run_id / stack / bucket / prefix / pages_listed / objects_scanned/indexed/updated / bytes_total / timing / kibana_url / dry_run
    Schema__Inventory__Wipe__Response      stack_name / indices_dropped / data_views_dropped / saved_objects_dropped / duration_ms
    Schema__Inventory__Run__Summary        per-row content of `inventory list`
  collections/
    List__Schema__S3__Object__Record
    List__Schema__Inventory__Run__Summary
  service/
    S3__Inventory__Lister                  boto3 boundary; paginate(bucket, prefix, max_keys, region) → (objects, page_count)
                                            + parse_firehose_filename() module-level helper
                                            + normalise_etag() module-level helper
    Inventory__HTTP__Client                sibling HTTP boundary (NOT extending Elastic__HTTP__Client per the brief promise);
                                            bulk_post_with_id() / delete_indices_by_pattern() / count_indices_by_pattern() /
                                            aggregate_run_summaries()
    Run__Id__Generator                     generates "{compact-iso8601}-{source}-{verb}-{shortsha}"
    Inventory__Loader                      orchestrator for load
    Inventory__Wiper                       orchestrator for wipe
    Inventory__Read                        orchestrator for list + health
    CF__Inventory__Dashboard__Builder      programmatic ndjson generator (Vis Editor, NOT Lens)
    CF__Inventory__Dashboard__Ids          shared id constants (used by builder + wiper, slice-2-ready)
```

### Data path

```
S3 (Firehose-written, AWS-managed)
   │
   ▼  list_objects_v2 (paginated)
S3__Inventory__Lister.paginate()
   │
   ▼  per object: parse filename + normalise etag + build record
List__Schema__S3__Object__Record (in memory)
   │
   ▼  group by delivery_at[:10]
{date: List__Schema__S3__Object__Record}
   │
   ▼  one bulk_post_with_id call per delivery date, _id = etag
sg-cf-inventory-{YYYY-MM-DD} indices (Elastic — throwaway)
   │
   ▼  data view + 5-panel dashboard (idempotent ensure)
Kibana — view, filter, snapshot
```

### Index naming (the bug-fixed version)

Indices are keyed on **delivery date** (the data's date), not load date.
A multi-day prefix (`--prefix 2026/04`) produces multiple per-day indices.
The data view `sg-cf-inventory-*` gathers them all; Discover and the
dashboard render a unified time-series across whatever days were loaded.

---

## Test coverage

- **150 unit tests** under
  `tests/unit/sgraph_ai_service_playwright__cli/elastic/lets/cf/inventory/`
- **Zero mocks.** Every collaborator has an `*__In_Memory` subclass.
  Three new ones for slice 1:
  - `S3__Inventory__Lister__In_Memory` (overrides `paginate()`)
  - `Inventory__HTTP__Client__In_Memory` (overrides `bulk_post_with_id` /
    `delete_indices_by_pattern` / `count_indices_by_pattern` /
    `aggregate_run_summaries`)
  - `Inventory__HTTP__Client__Recording_Requests` (test-only subclass for
    regression tests against the REAL HTTP path — overrides `request()`
    and feeds canned `Fake__Response` objects from a queue)
- Existing `Kibana__Saved_Objects__Client__In_Memory` was extended (test
  file only) with `find()` and `import_objects()` overrides.

Test breakdown:

| Area | Tests |
|------|-------|
| Phase 1 — schemas / primitives / enums / collections | 54 |
| Phase 2 — S3 lister + Firehose filename parser + etag normalise | 17 |
| Phase 3a — Inventory__HTTP__Client + Run__Id__Generator + Inventory__Loader | 20 |
| Phase 4 — Inventory__Wiper + dashboard ids constants | 16 |
| Phase 5 — CF__Inventory__Dashboard__Builder + loader integration | 13 |
| Phase 6 — Inventory__Read + count/aggregate HTTP methods | 21 |
| Real-HTTP regression tests (delete + count + aggregate) | 9 |

Existing 165 elastic tests stay green throughout.

---

## Notable bugs found and fixed during the slice

Five bugs surfaced during interactive smoke testing.  Three caused real
user-visible failures; two were pre-emptive design tweaks caught in unit
tests.

### Real failures caught by smoke

1. **`Safe_Str__Text` silently sanitised `:` in `kibana_url`.**
   The Type_Safe primitive replaced `:` and `/` with `_` (per its
   character-set rule), turning `https://1.2.3.4/` into
   `https___1.2.3.4_`.  Fix: switched the field type to `Safe_Str__Url`,
   which preserves URL chars.  Reused the existing
   `Schema__Elastic__Create__Response.kibana_url` precedent.

2. **boto3 region-empty produced `https://s3..amazonaws.com`.**
   Passing `region_name=''` to `boto3.client('s3', ...)` overrides the
   standard credential/region resolution chain (env vars, profile, IMDS)
   instead of falling through.  The CLI was threading a default `''`
   through to the lister.  Fix: `s3_client()` skips `region_name=` when
   the value is empty.  Plus added `region` as a first-class field on
   `Schema__Inventory__Load__Request` so `--region` actually works.
   Two regression tests pin both cases.

3. **Index name keyed on load date, not delivery date.**
   Loading `--prefix cloudfront-realtime/2026/04/25/` on 2026-04-26 sent
   every doc to `sg-cf-inventory-2026-04-26` instead of `-2026-04-25`.
   A multi-day prefix would have collapsed everything into one index,
   defeating the daily-rolling design.  Fix: group records by
   `delivery_at[:10]` and bulk-post once per delivery date.  Three new
   regression tests pin the grouping.

4. **Data view title was `sg-cf-inventory` (no wildcard).**
   The literal title couldn't match the literal index name
   `sg-cf-inventory-2026-04-25`.  Discover showed "No fields exist in
   this data view" until the user manually selected the index from the
   dropdown.  Fix: `DATA_VIEW__TITLE = 'sg-cf-inventory-*'`.

5. **Wildcard DELETE blocked by ES default `action.destructive_requires_name=true`.**
   `wipe` issued `DELETE /_elastic/sg-cf-inventory-*` and got HTTP 400
   "Wildcard expressions or all indices are not allowed".  The unit
   tests passed because the In_Memory subclass overrode the whole
   method.  Fix: list matching indices via `_cat/indices` (already
   done), then DELETE each one **by exact name**.  Tolerates per-index
   404 (race with concurrent delete).  Five regression tests against
   the REAL `request()` path pin the per-name behaviour, plus the
   "no wildcards in DELETE URLs" assertion.

6. **Storage class panel terms agg used `storage_class`, not `storage_class.keyword`.**
   Caught in the dashboard UI with "Saved field 'storage_class' of data
   view 'sg-cf-inventory-*' is invalid for use with the 'Terms'
   aggregation."  ES auto-mapping puts string enums under `text` with a
   `.keyword` sub-field; terms aggs need keyword.  Fix: changed the
   field to `storage_class.keyword`.  Regression test walks every
   visualization in the dashboard ndjson and asserts string-typed
   terms-agg fields end with `.keyword` (numeric fields are exempt).

### Pre-emptive design fix

7. **`Elastic__HTTP__Client.bulk_post()` was tightly typed to
   `List__Schema__Log__Document`.** Couldn't pass our
   `List__Schema__S3__Object__Record`, and even if we could, the method
   doesn't support `_id`-per-doc.  Decision: don't modify the existing
   client (the brief promised it stays unmodified, and the existing
   165 tests rely on its current shape).  Carved out a sibling
   `Inventory__HTTP__Client(Type_Safe)` with `bulk_post_with_id()` —
   accepts any `Type_Safe__List` and uses a named field as the `_id`.
   Cost: ~5 lines of `request()` duplication.  Worth it.

---

## Commit list

| SHA | Summary |
|---|---|
| `e583629` | brief — split-folder architecture brief at `team/comms/briefs/v0.1.99__sp-el-lets-cf-inventory/` (6 files) |
| `abc9b07` | brief — implementation phases (06) |
| `88b213f` | Phase 1 — Type_Safe foundations (15 prod + 15 test files, 54 tests) |
| `10f7229` | Phase 2 — S3 lister + Firehose filename parser + in-memory seam (17 tests) |
| `b413aea` | Phase 3a — Inventory__HTTP__Client + Run__Id__Generator + Inventory__Loader (20 tests) |
| `5e84c6b` | Phase 3b — CLI wiring (`scripts/elastic_lets.py` + +2 lines in `scripts/elastic.py`) |
| `5fde394` | fix — empty region must fall through to boto3 default chain |
| `377e917` | chore — gitignore poetry.lock |
| `4315866` | fix — index by delivery date + data-view wildcard pattern (3 regression tests) |
| `1b4f4b9` | Phase 4 — Inventory wiper + `wipe` CLI (16 tests) |
| `fee0bee` | Phase 5 — CF inventory dashboard auto-imported on load (13 tests) |
| `5b521c8` | fix — wipe must DELETE per-index, wildcard blocked by ES (5 regression tests) |
| `f0fa5b0` | Phase 6 — list + health verbs (21 tests) |
| `f34ed56` | fix — storage_class terms agg must use .keyword sub-field (1 regression test) |

---

## Good failures vs bad failures

Following the project's debrief convention.

### Good failures (surfaced early, caught by tests, informed a better design)

- **`Safe_Str__Text` `/` → `_` sanitisation** caught by the very first
  Phase 1 unit test that asserted on the schema's `schema_version`
  default.  Drove the `_v1` separator convention and the later
  `Safe_Str__Url` switch.
- **boto3 region empty-string** caught the moment the user ran the first
  real `--dry-run`.  Drove a regression-test pattern (using
  `boto3.client.meta.region_name`) that doesn't require AWS credentials
  to verify.
- **Wildcard DELETE blocked by ES** caught by the user's first wipe.
  Drove the introduction of the `Inventory__HTTP__Client__Recording_Requests`
  test pattern — the first regression test in the project against the
  real HTTP path of an `Inventory__*` class.
- **storage_class missing `.keyword`** caught by the user opening the
  dashboard and seeing the panel's red triangle.  Drove the regression
  test that walks every dashboard visualization and asserts the
  string-vs-numeric terms-agg-field rule.
- **Lens / Vis Editor dichotomy** — clarified during the conversation
  about why Phase 5 sticks to legacy `visualization`: Lens is fine
  *when exported by Kibana's UI* (carries the right migration metadata)
  but unsafe *when hand-authored* (the migration footguns from the
  v0.1.46 sp-elastic-kibana debrief).  Codified in
  `CF__Inventory__Dashboard__Builder`'s module header.

### Bad failures (silenced, worked around, or re-introduced — i.e. follow-up requests)

- **None this slice.** Every bug surfaced was reproduced as a regression
  test before being fixed.  The "real HTTP path" coverage gap (where
  the In_Memory subclass overrides hide bugs in production code) was
  closed proactively after the wildcard-DELETE incident.

See part 3 ("How to use it") for the user-facing recipes.