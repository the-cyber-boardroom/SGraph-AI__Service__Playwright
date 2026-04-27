# 08 — Elastic Optimisations

**Status:** 🟡 STUB — to be expanded by Sonnet in Phase 0

---

## Purpose of this doc

Detailed treatment of the seven Elastic write-path optimisations (E-1 through E-7) introduced in this slice. For each: today's behaviour, proposed behaviour, expected gain, backward-compatibility strategy, test approach.

These optimisations are **additive** — they extend `Inventory__HTTP__Client` with new optional parameters whose defaults preserve current behaviour. Existing slices 1 & 2 inherit the wins automatically once their callers opt in.

---

## Sections to include

### 1. Why these belong in this slice

The C-stage's bulk-post path is the natural place to introduce these optimisations because it's the densest write path in the codebase — one bulk-post per consolidated day, plus one `_update_by_query` per consolidation, plus one manifest doc index. The optimisations make that path land in <0.5 sec instead of ~1 sec, *and* slices 1 & 2 inherit them transitively. Two birds, one shared HTTP client.

### 2. Per-optimisation deep dive

For each of E-1 through E-7, structure the doc section as:

- **What it does** (one-paragraph plain-language explanation)
- **Today** (current behaviour with code reference, e.g. `Inventory__HTTP__Client.bulk_post_with_id` line N)
- **Proposed** (new behaviour, full method signature change if any)
- **Expected gain** (cite the README §"Estimated combined impact")
- **Backward compat** (how the default preserves existing behaviour)
- **Test approach** (what the in-memory subclass needs to record so we can assert callers opted in correctly)
- **Caller migration** (which callers in this slice opt in; whether to migrate slices 1 & 2 in this PR or defer)

#### E-1 — `?refresh=false` on bulk-post

Tag: 40–60% off `post:` timing on big batches.

- **What it does:** ES default is to refresh the index after every bulk request, which makes new docs immediately searchable but blocks the request until the refresh completes. For batch loads where we don't need real-time search, `?refresh=false` lets the request return as soon as the docs are durable.
- **Today:** No `?refresh=` param on the URL — defaults to `false` in newer ES versions but inconsistently honoured. Worth being explicit.
- **Proposed:** Optional `refresh: bool = True` parameter on `bulk_post_with_id`. Default preserves current behaviour. Callers in batch contexts opt in with `refresh=False`. One explicit `_refresh` call at the end of a batch run if needed.
- **Test:** In-memory subclass records the URL parameters; assertion that `Consolidate__Loader` calls with `refresh=False`.

#### E-2 — `?routing={date}` for daily indices

Tag: 10–20% off post latency for high-doc-count batches.

- **What it does:** Pins all docs of a day to one shard at write time, removing scatter-gather coordination on writes. Read queries for the day's index also stay shard-local.
- **Today:** No routing — docs are spread by the default hash.
- **Proposed:** Optional `routing: str = ''` parameter. When non-empty, appended as `?routing={value}`.
- **Caveat:** Single-shard daily indices already get this for free. The win is for multi-shard indices, which we don't have today but might if traffic grows. Document as future-proofing.
- **Test:** In-memory subclass records routing; assertion that callers pass the date.

#### E-3 — HTTP keep-alive / connection pool

Tag: ~100ms off every call after the first.

- **What it does:** Reuses a TLS connection across requests to the same host, eliminating the TLS handshake cost on every call.
- **Today:** Each `Inventory__HTTP__Client.request()` likely opens a fresh connection (unverified — Sonnet to confirm during Phase 0 by reading the `request()` method).
- **Proposed:** Class-level `requests.Session()` initialised in `__init__`, used for all calls within the lifetime of the `Inventory__HTTP__Client` instance.
- **Caller migration:** No call-site changes needed. The Session is internal to the client.
- **Test:** Hard to test directly without a real server; covered by integration test against the live Ephemeral Kibana stack in Phase 6's demo.

#### E-4 — Pre-created index template + mapping

Tag: eliminates the `.keyword` footgun.

- **What it does:** Defines the mapping for `sg-cf-events-*`, `sg-cf-inventory-*`, `sg-cf-consolidated-*`, `sg-pipeline-runs-*` *before* any doc is indexed. Prevents ES auto-mapping from inferring the wrong type (typically string fields auto-mapping with `.keyword` sub-fields, which then breaks aggregations).
- **Today:** Auto-mapping runs on first doc per index. Slice 2's reality doc documents one case where this caused a Lens panel to fail.
- **Proposed:** `consolidate health` (and existing `events health`, `inventory health`) ensures the template exists. If missing, creates it. Idempotent.
- **Test:** In-memory client records the PUT to `_template/sg-cf-consolidated`; assertion that `health` calls it.

#### E-5 — Bulk-post body size cap with auto-split

Tag: prevents ES OOM rejections on edge cases.

- **What it does:** ES recommends bulk request bodies in the 5–15 MB range. We currently ship one bulk per day, which is fine at today's volume (~565 events × ~2 KB each ≈ 1 MB) but doesn't scale. This optimisation auto-splits large bulks at a configurable threshold.
- **Today:** Single bulk request regardless of size.
- **Proposed:** Optional `max_bytes: int = 0` parameter. `0` = no split (current behaviour). `>0` = auto-split at that byte count. Default for the C-stage: `10 * 1024 * 1024` (10 MB).
- **Edge case:** A single doc bigger than `max_bytes`. Must not split mid-doc — emit it alone in its own request, even if oversized. ES will accept it (with a warning) rather than reject it.
- **Test:** Construct a `List` of records totaling > `max_bytes`, assert two requests; construct a `List` with one giant record, assert one request.

#### E-6 — `_update_by_query` with `terms` filter for manifest flips

Tag: N× speedup on manifest update.

- **What it does:** Today's slice-2 code flips `content_processed` one etag at a time across N HTTP calls. The `terms` query lets us flip all N etags in one call.
- **Today:** N HTTP calls with `term: {etag: <value>}`.
- **Proposed:** New method `Inventory__Manifest__Updater.mark_processed_batch(etags: List, run_id: str)` that issues one `_update_by_query` with `{"terms": {"etag": [<all etags>]}}`.
- **Caller migration:** `Consolidate__Loader` uses the new batch method. `Events__Loader`'s existing per-file `mark_processed` stays for now (used by the per-file path, which is not the bottleneck if you're using consolidation). A v0.1.102+ pass can migrate it.
- **Test:** In-memory subclass records the request body; assertion that the terms list contains every expected etag.

#### E-7 — Bulk-post `?timeout=` and `?wait_for_active_shards=1`

Tag: defensive — prevents single-replica yellow-cluster stalls.

- **What it does:** Explicit timeout and primary-only acknowledgement. Defaults to "wait for primary, 30 second timeout" — protects against a yellow-cluster scenario where the replica isn't healthy.
- **Today:** ES defaults to "wait for active shards" which can stall on yellow.
- **Proposed:** Two new optional parameters with sensible defaults. Existing behaviour preserved if defaults are not changed.
- **Test:** In-memory subclass records the URL parameters; assertion that callers pass the expected timeout.

### 3. Estimated combined impact (cite the README)

Re-render the table from the README §"Estimated combined impact":

```
   Before any ES optimisation (consolidation alone):  ~660 ms wall time
   After E-1 (refresh=false):                         ~520 ms
   After E-1 + E-3 (keep-alive):                      ~430 ms
   After E-1 + E-3 + E-6 (terms _update_by_query):    ~330 ms

   Compared to today's per-file pipeline (~9.4 sec for 21 files):
     = ~28× speedup
```

### 4. New `bulk_post_with_id` signature

Show the full new signature with all optional parameters (cite the README §"Where these optimisations live in the code"). Document the parameter order; new params come AFTER existing ones to preserve backward compatibility.

### 5. Test infrastructure changes

The `Inventory__HTTP__Client__In_Memory` subclass needs new recording surfaces:

```python
class Inventory__HTTP__Client__In_Memory(Inventory__HTTP__Client):
    bulk_calls : List__Schema__Bulk__Call = ...   # records refresh, routing, max_bytes per call
    update_by_query_calls : ... = ...             # records terms list
    posted_with(refresh, routing, max_bytes) -> bool   # assertion helper
```

### 6. What's NOT in this slice

- HTTP/2 to ES — Elastic 8.13 doesn't enable it by default.
- Async I/O for the loader — would need rethinking the Type_Safe model. Out of scope.
- ES bulk error retry with exponential backoff — defer to v0.1.103+ if intermittent failures become a real problem.
- Compression on the wire (`Content-Encoding: gzip` for the bulk body) — flagged as a v2 follow-up; ES supports it but the extra CPU is rarely worth it on local-network paths.

---

## Source material

- README §"Elastic optimisations" — the source of truth for every entry
- `Inventory__HTTP__Client.py` — the class being modified
- Slice 2 reality doc on the `.keyword` mapping issue — context for E-4
- ES official guide on bulk request sizing — context for E-5

---

## Target length

~150–200 lines.
