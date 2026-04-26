# 2026-04-26 — `sp el lets cf events` (LETS slice 2) — 2 / 3 — What we built

This is part two of the three-part debrief.

| Part | File |
|------|------|
| 1 — Why we built this | `2026-04-26__lets-cf-events__01-why.md` |
| 2 — **What we built** *(this doc)* | `2026-04-26__lets-cf-events__02-what.md` |
| 3 — How to use it | `2026-04-26__lets-cf-events__03-how-to-use.md` |

---

## CLI surface

`sp el lets cf events ...` — four verbs, parallel to slice 1's inventory.

### Lifecycle (load + wipe — matched pair)

| Command | What it does |
|---|---|
| `sp el lets cf events load [--prefix Y[/M[/D]]] [--all] [--max-files N] [--from-inventory] [--dry-run] [--run-id ID] [--bucket B] [--password P] [--region R]` | Build queue (S3 list OR manifest) → fetch each `.gz` → gunzip → parse TSV → ensure data view + dashboard → bulk-post records to per-day index → flip inventory manifest's `content_processed=true` |
| `sp el lets cf events wipe [-y] [--password P] [--region R]` | Drop every `sg-cf-events-*` index (per-name); drop data view `sg-cf-events-*`; drop dashboard + visualisations; reset every inventory doc's `content_processed` back to false |

### Read-only

| Command | What it does |
|---|---|
| `sp el lets cf events list [--top N]` | Distinct `pipeline_run_id` values currently indexed; per-row event count, file count (cardinality on `source_etag.keyword`), bytes total, event range, last loaded |
| `sp el lets cf events health` | Four checks: `events-indices`, `events-data-view`, `events-dashboard`, plus a bonus `inventory-link` row showing "X of Y inventory docs processed (Z%)" |

---

## Architecture

### Module tree

```
sgraph_ai_service_playwright__cli/elastic/lets/cf/events/
  enums/
    Enum__CF__Method                           GET / POST / PUT / ... / OTHER (8 verbs)
    Enum__CF__Protocol                         http / https / ws / wss / other (lowercase wire form)
    Enum__CF__Edge__Result__Type               Hit / RefreshHit / OriginShieldHit / Miss / Error /
                                                LimitExceeded / Redirect / FunctionGeneratedResponse / Other
    Enum__CF__SSL__Protocol                    TLSv1.0–1.3 + OTHER (dotted wire form)
    Enum__CF__Status__Class                    1xx / 2xx / 3xx / 4xx / 5xx / other (derived from sc_status)
    Enum__CF__Bot__Category                    HUMAN / BOT_KNOWN / BOT_GENERIC / UNKNOWN
  primitives/
    Safe_Str__CF__Country                      ISO-3166 alpha-2; uppercase only (parser uppercases pre-construction)
    Safe_Str__CF__Edge__Location               POP code, e.g. "HIO52-P4"
    Safe_Str__CF__Edge__Request__Id            base64-ish, ~52 chars
    Safe_Str__CF__URI__Stem                    URL path; up to 2048 chars
    Safe_Str__CF__User__Agent                  printable ASCII; capped at 500 chars
    Safe_Str__CF__Referer                      printable ASCII; capped at 1024
    Safe_Str__CF__Host                         RFC-952/1123 hostname; lowercased
    Safe_Str__CF__Cipher                       IANA cipher names; uppercase only
    Safe_Str__CF__Content__Type                MIME with parameters; lowercased
  schemas/
    Schema__CF__Event__Record                  38 fields (the indexed doc)
    Schema__Events__Load__Request              + from_inventory flag, region field
    Schema__Events__Load__Response             per-file + aggregate counts + queue_mode + inventory_updated
    Schema__Events__Wipe__Response             + inventory_reset_count
    Schema__Events__Run__Summary               event_count + file_count (distinct etags) + bytes_total + ranges
  collections/
    List__Schema__CF__Event__Record
    List__Schema__Events__Run__Summary
  service/
    S3__Object__Fetcher                        boto3 boundary — get_object_bytes(bucket, key, region)
                                                + In_Memory subclass (dict fixture)
    Bot__Classifier                            UA → Enum__CF__Bot__Category in 3 steps
                                                (28 named regexes → 5 generic word-bounded → HUMAN/UNKNOWN)
    CF__Realtime__Log__Parser                  TSV → records + Stage 1 derivations in single pass
                                                + module-level helpers (gunzip, parse_unix_to_iso,
                                                  parse_seconds_to_ms, parse_int_or, parse_dash_or,
                                                  status_class_from_int, safe_enum, clean_user_agent,
                                                  clean_referer, normalise_country/edge_location/cipher)
    Inventory__Manifest__Reader                Queries sg-cf-inventory-* for content_processed=false docs
    Inventory__Manifest__Updater               mark_processed(etag, run_id) + reset_all_processed()
    Events__Loader                             Orchestrator (queue → fetch → parse → bulk-post → manifest update)
    Events__Wiper                              4-step idempotent reset
    Events__Read                               list_runs + health (4 checks)
    CF__Events__Dashboard__Builder             6-panel ndjson generator (Vis Editor)
    CF__Events__Dashboard__Ids                 Shared id constants (used by builder + wiper)
```

CLI lives in `scripts/elastic_lets.py` (additive — slice 1 already
mounted the `lets` typer app on `scripts/elastic.py`).

### Data path

```
S3 cloudfront-realtime/ (Firehose-written)
   │
   ▼  GetObject (per file)
gzipped bytes
   │
   ▼  gzip.decompress
TSV string
   │
   ▼  CF__Realtime__Log__Parser.parse() — single pass
List__Schema__CF__Event__Record + lines_skipped count
   │
   ▼  loader stamps source_bucket/source_key/source_etag/doc_id/run_id/loaded_at
   │
   ▼  group by event timestamp[:10]
{date: List__Schema__CF__Event__Record}
   │
   ▼  one bulk_post_with_id per day, _id = doc_id ("{etag}__{line_index}")
sg-cf-events-{YYYY-MM-DD} indices (Elastic — throwaway)
   │
   ▼  data view + 6-panel dashboard (idempotent ensure)
Kibana — explore, filter, snapshot
   │
   ▼  AND in parallel: per-file _update_by_query
sg-cf-inventory-* docs flipped to content_processed=true
```

### Doc identity (per-event)

`_id = "{source_etag}__{line_index}"` extends slice 1's etag-as-id
idempotency to per-line granularity.  Properties:

- Re-loading the same `.gz` overwrites in place (etag stable per file)
- Different `.gz` files never collide (different etag)
- Within one file each line is uniquely identified
- `source_etag` is also a separate field on the doc, so a join from
  events back to inventory by `terms(source_etag)` is one query

### Index naming

`sg-cf-events-{YYYY-MM-DD}` keyed on each event's `timestamp[:10]`
(NOT loaded_at — slice 1's bug-fix lesson reapplied).  Multi-day prefix
loads correctly produce multiple per-day indices.  The data view
`sg-cf-events-*` gathers them; Discover and the dashboard render
unified time-series across whatever days are loaded.

---

## Test coverage

- **201 unit tests** under
  `tests/unit/sgraph_ai_service_playwright__cli/elastic/lets/cf/events/`
- **Zero mocks** — every external collaborator has an `*__In_Memory`
  subclass.

Test breakdown:

| Phase | Area | Tests |
|-------|------|-------|
| 1 | Schemas / primitives / enums / collections | 77 |
| 2 | TSV parser + S3 fetcher + bot classifier + parser helpers | 66 |
| 3 | Manifest reader + updater + Events__Loader | 21 |
| 5 | Events__Wiper + dashboard ids | 14 |
| 6 | Dashboard builder + Events__Read | 25 |

Plus 1 update to test_Schema__CF__Event__Record (37→38 fields after
adding `doc_id`) and 3 new tests in test_Events__Loader for the
dashboard auto-import path.

531 total elastic tests pass.  The previous 165 base + 165 slice-1
LETS + 201 slice-2 LETS — all green.

---

## Notable bugs found and fixed during the slice

Six bugs surfaced during interactive smoke testing or unit-test runs.
All classified as "good failures" — caught early, regression test
added, design improved.

### Slice 2 specific

1. **`Safe_Str.to_upper_case` doesn't exist.**  Three primitives
   (`Safe_Str__CF__Country`, `..__Edge__Location`, `..__Cipher`) tried
   to use `to_upper_case = True` for case normalisation.  osbot-utils
   only supports `to_lower_case`.  Fix: dropped the no-op attribute,
   made the regex strict (uppercase only), updated docs to note the
   parser uppercases before construction.

2. **Bot classifier word boundaries.**  Initial generic-bot pattern
   `bot/` matched `NonBotProduct/2.0` (false positive).  Fix: word-
   bounded regex for `\bspider\b`, `\bcrawler\b`, etc.  Dropped the
   `bot/` indicator entirely (too prone to false positives — known
   bots are caught by the named-bot list anyway).

3. **`Safe_Str__Text` sanitises `/` (slice 1 lesson reapplied).**
   The error-message format string `f'fetch/gunzip {key}: ...'` had
   `/` sanitised to `_` when stored in `Schema__Events__Load__Response.
   error_message`.  Fix: changed format to `f'fetch error on {key}:
   ...'` (no `/`).

4. **Forgot `doc_id` field on Schema__CF__Event__Record initially.**
   The brief specified per-event `_id = "{etag}__{line_index}"` for
   idempotency, but I built the schema with `source_etag + line_index`
   as separate fields and tried to use `id_field='source_etag'` on
   bulk_post_with_id.  That gave per-FILE not per-LINE uniqueness.
   Fix: added `doc_id : Safe_Str__Text` field (38 fields total now);
   loader stamps it as `f'{etag}__{line_index}'` before bulk-post;
   uses `id_field='doc_id'`.  Updated the schema field-count test.

### Test fixture bugs

5. **`{} or default` returns the default.**  Empty dict is falsy in
   Python, so `fixture_objects or {SAMPLE_KEY: SAMPLE_GZ}` short-circuits
   to the default when an empty fixture is intentionally requested.
   Fix: `if fixture_objects is not None`.

6. **Single-char bucket name fails Safe_Str__S3__Bucket regex.**  Test
   data used `bucket='b'` for brevity; the regex requires 3-63 chars
   per AWS rules.  Fix: realistic test bucket names.

---

## Commit list

| SHA | Summary |
|---|---|
| `2e1cf69` | brief — split-folder architecture brief at `team/comms/briefs/v0.1.100__sp-el-lets-cf-events/` (6 files) |
| `d46a759` | Phase 1 — Type_Safe foundations (22 prod + 22 test files, 77 tests) |
| `ad760e6` | Phase 2 — TSV parser + S3 fetcher + Bot__Classifier (66 tests) |
| `c7e2bc7` | Phase 3 — manifest reader/updater + Events__Loader (21 tests) |
| `4e8f1c8` | Phase 4 — `sp el lets cf events load` CLI |
| `390e12f` | Phase 5 — Events__Wiper + CF__Events__Dashboard__Ids + `wipe` CLI (14 tests) |
| `38f61f0` | Phase 6 — CF__Events__Dashboard__Builder + Events__Read + `list`/`health` CLI (25 tests) |

7 commits.  Plus the prior session's `9aa88f6` (sp el forward / health
hint) and `b365adf` (slice 1 closer) which are not part of slice 2 but
sit on the same branch.

---

## Good failures vs bad failures

Following the project's debrief convention.

### Good failures (surfaced early, caught by tests, informed a better design)

- **`to_upper_case` not supported** — caught by a Phase 1 unit test the
  moment a primitive was instantiated.  Drove the "parser normalises
  case before construction" convention, captured in each affected
  primitive's header.
- **Bot classifier word boundaries** — caught by a unit test asserting
  `NonBotProduct/2.0` should classify as HUMAN.  Drove the regex-
  with-word-boundaries refactor and the explicit "we don't try to
  catch generic `bot/` patterns" comment.
- **`Safe_Str__Text` `/` sanitisation in error_message** — caught by
  the loader's error-path test.  Drove a repeat of slice 1's lesson:
  format strings that get stored in Type_Safe fields can't use `/`.
- **`doc_id` field forgotten** — caught when writing the loader test
  that asserts `id_field='doc_id'` after the schema only had source_etag.
  Drove the schema update + the test that explicitly verifies
  `doc_id == "{etag}__{line_index}"` for each record.
- **Bot classifier promoted to a class with the rule lists module-
  level** — initial design had inline rules in the loader.  Refactored
  to a Type_Safe class so the rule lists are easy to extend by
  subclassing.

### Bad failures (silenced, worked around, or re-introduced — i.e. follow-up requests)

- **None this slice.** Every bug surfaced was reproduced as a
  regression test before being fixed.  The "events-updated: 5 on a
  fresh stack" the user spotted during smoke (between slice 1 close
  and slice 2 Phase 4) was traced to a re-run; not a slice-2 bug.

See part 3 for the user-facing recipes.