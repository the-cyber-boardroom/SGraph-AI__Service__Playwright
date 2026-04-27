# Brief: `sp el lets cf consolidate` — third LETS slice (the C-stage)

**Version:** v0.1.101
**Date:** 2026-04-27
**Audience:** Dev (Claude Code Sonnet session), Architect (review), QA, Librarian
**Status:** PROPOSED — nothing described here exists yet
**Branch base:** `dev` (HEAD `3ba5878` at brief time)
**Companion docs (architect, read first):**
- `00__cloudfront-lets-architecture-review.md` — end-to-end picture of the existing pipeline
- `00b__consolidation-lets-pattern.md` — the architectural rationale and the generalisable pattern

**Revision history:**
- v1 (2026-04-27 morning) — initial draft
- v2 (2026-04-27 afternoon) — incorporated Dinis's refinements: lets-config.json at folder root, S3 reorganisation under `lets/`, ES optimisations section, future-work pattern (consolidate / compress / expand), triggered execution roadmap

---

## One-paragraph summary

The CloudFront LETS pipeline today processes ~425 small `.gz` files per day (median ~7 events each), paying ~440 ms of fixed per-file overhead — S3 GetObject round-trip, Elasticsearch bulk-post, manifest `_update_by_query` — to do roughly 8 ms of actual parsing work. Real-work-to-wrapper ratio: 1:50. This slice introduces a **C (Consolidate) stage between L and E**, making the pipeline L-C-E-T-S. Once per day, `sp el lets cf consolidate load` fetches every unprocessed source `.gz` for a date, parses it through the existing `CF__Realtime__Log__Parser`, concatenates the parsed events into a single `events.ndjson.gz` artefact, persists that artefact + a manifest sidecar to a new S3 prefix, and flips a new `consolidation_run_id` field on each source inventory doc. A new `events load --from-consolidated` flag then reads the consolidated artefact in one S3 GetObject + one ES bulk-post, instead of 425. **Measured projected speedup: ~14× on the events load step (rising to ~28× after the bundled ES optimisations land).** The pattern is intentionally generalisable — once `Consolidate__Loader` exists, it plugs into mitmproxy flows, Playwright session artefacts, MCP tool-call logs, and audit logs by swapping only the parser. This brief also lays the groundwork for the broader **LETS workflow taxonomy** (consolidate / compress / expand) and the **trigger model** (manual today, scheduled / event-driven future) that subsequent slices will inhabit.

---

## Why this brief exists

A live trace from `events load` showed the bottleneck is **per-file fixed overhead**, not per-event work:

```
  per-file breakdown (median)
                  ┌─────┬─────┬───────┬──────┬──────┐
                  │ s3  │ gz  │ parse │ post │ mark │
                  ├─────┼─────┼───────┼──────┼──────┤
                  │ 175 │  0  │   8   │ 141  │ 102  │   ms
                  │ 41% │ 0%  │   2%  │ 33%  │ 24%  │
                  └─────┴─────┴───────┴──────┴──────┘
```

Three of the five timing buckets are pure HTTP round-trip overhead. Solving this once — in a way that respects the LETS principle of "persist before indexing" — is the slice's purpose.

This also reframes consolidation as **the LETS principle taken seriously**: today the pipeline persists L (Firehose drops) and S (ES indices) but treats E (parsing + classification) as ephemeral. Every re-load redoes the parse work. The consolidated artefact captures the parsed-and-classified state with parser version stamped on it, so E becomes "the cheap function that re-runs on demand" exactly as the principle intended.

---

## File index

| File | Purpose | Status |
|------|---------|--------|
| `README.md` *(this file)* | Status, summary, decisions, file index | ✅ This brief |
| `00__cloudfront-lets-architecture-review.md` | End-to-end picture of the existing pipeline | ✅ Architect grounding |
| `00b__consolidation-lets-pattern.md` | Architectural rationale + generalisable pattern | ✅ Architect grounding |
| `01__principle-and-stages.md` | LETS becomes L-C-E-T-S; what changes vs slice 2 | 🟡 Sonnet to expand |
| `02__cli-surface.md` | Verbs, flags, output examples; new `--from-consolidated` mode | 🟡 Sonnet to expand |
| `03__schemas-and-modules.md` | New schemas (Manifest, Source, ConsolidateRun, Lets__Config), module tree, S3__Object__Writer boundary | 🟡 Sonnet to expand |
| `04__elastic-and-dashboard.md` | New `sg-cf-consolidated-{date}` index + 1-panel dashboard "what's been consolidated" | 🟡 Sonnet to expand |
| `05__acceptance-and-out-of-scope.md` | Acceptance criteria; what defers to v0.1.102 (orchestrator) and v0.1.103+ | 🟡 Sonnet to expand |
| `06__implementation-phases.md` | PR-sized phases for Dev pickup | 🟡 Sonnet to expand |
| `07__s3-reorganisation.md` | The `cloudfront-realtime/` → `lets/` prefix reorganisation — pre-requisite phase | 🟡 Sonnet to expand |
| `08__elastic-optimisations.md` | ES write-path optimisations (refresh, routing, batch sizing, mapping templates, connection reuse) | 🟡 Sonnet to expand |
| `09__lets-workflow-taxonomy.md` | Future workflows: consolidate / compress / expand — the pattern landscape | 🟡 Sonnet to expand |
| `10__trigger-model-roadmap.md` | From manual CLI today → scheduled cron → S3-event-driven serverless | 🟡 Sonnet to expand |

---

## Architect's locked decisions for this slice

These are settled. The Sonnet Dev session implements against them; if any seem wrong, raise it as an Architect-review request — do not silently change them.

### Naming, persistence, and identity

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | **New verb tree** — `sp el lets cf consolidate {load,wipe,list,health,verify}` | Sibling to `inventory` and `events`; same shape, same auto-stack-pick, same `--dry-run` / `--run-id` conventions. |
| 2 | **Output goes to the same S3 bucket, new top-level `lets/` prefix** — see decision #5 for the full layout | One IAM policy, one lifecycle rule, no cross-bucket coordination. Source `cloudfront-realtime/` is never modified or deleted. |
| 3 | **Output format: NDJSON.gz** | Honours the LETS "human-readable + grep-able" property. Parquet is a future Tier 3 if columnar reads become a need. One event per line — same shape the parser already produces. |
| 4 | **Granularity: per-day default**, with `--granularity hour` flag for future use | Matches the existing `sg-cf-events-{YYYY-MM-DD}` index naming. |

### S3 layout and config-at-folder-root *(REVISED — v2)*

| # | Decision | Rationale |
|---|----------|-----------|
| 5 | **Hierarchical layout with `lets-config.json` at the root of each compatibility region:** see diagram below | Solves "what produced this output" without filename pollution. If parser/schema breaks compatibility, output goes to a sibling region with its own config. Source `.gz` files live in `cloudfront-realtime/` (Firehose's destination — we do not control this); consolidated artefacts live under our `lets/` prefix. |

```
   s3://745506449035--sgraph-send-cf-logs--eu-west-2/

   ├── cloudfront-realtime/                        ← Firehose target (UNTOUCHED)
   │   └── 2026/04/27/EXXX....{uuid}.gz
   │
   └── lets/                                       ← LETS workspace (we own this)
       │
       ├── raw-cf-to-consolidated/                 ← Workflow region: consolidate
       │   ├── lets-config.json                    ← compat-root config (see below)
       │   ├── 2026/04/27/
       │   │   ├── manifest.json                   ← per-day sidecar
       │   │   └── events.ndjson.gz                ← consolidated artefact
       │   ├── 2026/04/26/
       │   │   ├── manifest.json
       │   │   └── events.ndjson.gz
       │   └── …
       │
       ├── raw-cf-to-consolidated__v2/             ← if parser breaks compat, NEW region
       │   ├── lets-config.json                    ← new config, new compat boundary
       │   ├── 2026/04/27/…
       │   └── …
       │
       ├── consolidated-to-rolled-up/              ← FUTURE: a compress workflow
       │   ├── lets-config.json
       │   └── …
       │
       └── per-event-screenshots/                  ← FUTURE: an expand workflow
           ├── lets-config.json
           └── …
```

**`lets-config.json` schema (at compatibility-region root):**

```json
{
   "config_version":           "1",
   "workflow_type":            "consolidate",
   "input_source": {
      "type":                  "s3",
      "bucket":                "745506449035--sgraph-send-cf-logs--eu-west-2",
      "prefix":                "cloudfront-realtime/",
      "format":                "cf-realtime-tsv-gz"
   },
   "output_format": {
      "type":                  "ndjson-gz",
      "schema":                "Schema__CF__Event__Record",
      "schema_version":        "v1",
      "compression":           "gzip"
   },
   "implementations": {
      "parser":                "CF__Realtime__Log__Parser",
      "parser_version":        "v0.1.100",
      "bot_classifier":        "Bot__Classifier",
      "bot_classifier_version":"v0.1.100",
      "consolidator":          "Consolidate__Loader",
      "consolidator_version":  "v0.1.101"
   },
   "compatibility_boundary": {
      "rule":                  "any change to schema, parser_version major, or bot_classifier categories => new compatibility-region folder",
      "examples_of_breaks":    ["new field on Schema__CF__Event__Record",
                                "removed field on Schema__CF__Event__Record",
                                "Enum__CF__Bot__Category gains/loses a value",
                                "parser_version major bump (v1.x → v2.x)"]
   },
   "created_at":               "2026-04-27T03:00:00Z",
   "created_by":               "sp el lets cf consolidate load (run cons-2026-04-27-abc123)"
}
```

**The compatibility boundary is the central insight:** everything below a `lets-config.json` is guaranteed produced by the same toolchain. If anything breaks compat, you create a new sibling folder with its own config — the old data stays readable forever. Readers (e.g. `events load --from-consolidated`) check the config first, refuse to read incompatible regions, and surface a clear error.

| # | Decision | Rationale |
|---|----------|-----------|
| 5b | **`lets-config.json` is the `events load --from-consolidated` validation target** — reader checks it before reading any artefact | Forces an explicit compatibility check on every read. Drift between writer and reader becomes a failed health check, not a silent corruption. |
| 5c | **Per-day `manifest.json` sidecar** carries the run-specific data (source-etag list, event count, run_id, started_at, finished_at, durations) | Compat-root config = "what tool produced this region." Per-day manifest = "what happened on this specific run." Two separate concerns, two separate files. |
| 5d | **Filenames stay clean** — `events.ndjson.gz`, `manifest.json` | No version-in-filename. The folder placement is the version assertion. |

### Source-side changes

| # | Decision | Rationale |
|---|----------|-----------|
| 6 | **Manifest dual-persisted** — JSON sidecar in S3 (durable record) AND a doc in `sg-cf-consolidated-{date}` (Kibana visibility) | The S3 sidecar is the source of truth; the ES doc is the index. Same dual pattern as inventory docs vs source `.gz` files. |
| 7 | **New `consolidation_run_id` + `consolidated_at` fields on `Schema__S3__Object__Record`** | Same flip pattern as `content_processed`/`content_extract_run_id`, alongside (not replacing) those fields. One `_update_by_query` per consolidation run, scoped to the source-etag set via a `terms` query. |
| 8 | **`events load --from-consolidated`** is a new third queue mode | Joins existing default (S3-listing) and `--from-inventory`. Reads the consolidated NDJSON, validates against `lets-config.json`, maps each line back to its `Schema__CF__Event__Record`, bulk-posts in ONE call per day. |

### Idempotency, wipe, and boundaries

| # | Decision | Rationale |
|---|----------|-----------|
| 9 | **Idempotency:** content-addressed by source-etag-set within a compat region | Re-running consolidation for the same date with the same source set produces a byte-identical output. New source files since last run → re-run extends. Parser change → goes to a new compat region. |
| 10 | **Wipe semantics:** `consolidate wipe` deletes consolidated S3 artefacts (the date subtree under the compat region) AND the `sg-cf-consolidated-*` index AND clears the `consolidation_run_id` flag on inventory. The source `cloudfront-realtime/` prefix is **never touched**. The compat-region `lets-config.json` is kept (it's metadata about the region, not the data). | Matched-pair rule. Source is reproducible; consolidated artefacts are derivative and disposable. |
| 11 | **No new boto3 calls outside `S3__*` boundary classes** | New class `S3__Object__Writer` (sibling of `S3__Object__Fetcher`) is the only new boto3 surface. Consolidation orchestrator uses it; orchestrator itself stays pure-logic. |
| 12 | **No mocks, no patches** — `S3__Object__Writer__In_Memory` collects writes; existing `*__In_Memory` classes reused | Same testing pattern as slices 1 & 2. ~150–200 unit tests expected. |
| 13 | **`Pipeline__Runs__Tracker` integration** — every `consolidate load` records one journal doc with verb `CONSOLIDATE` (new enum value) | Extends the Phase B journal pattern. Adds one line to `Enum__Pipeline__Verb`. |
| 14 | **CLI-only this slice** — no FastAPI routes | Consistent with `sp el` as a whole being CLI-only per v0.1.96 locked decision #4. The orchestrator brief (v0.1.102) inherits this stance. |
| 15 | **Reality doc updated in the same PR** — adds `12__lets-cf-consolidate.md` to `team/roles/librarian/reality/v0.1.101/` | Code authors update reality. The PR is not mergeable without this. |

---

## Elastic optimisations *(NEW — v2 §)*

The current `Inventory__HTTP__Client.bulk_post_with_id` ships records correctly but leaves measurable performance on the table. This slice's bulk-post path is a natural place to fix that — and the fixes are inherited by every existing caller (slices 1 & 2 benefit too). All changes are additive: new optional parameters with backward-compatible defaults, never behaviour changes for existing call sites.

### What we can do today (no infrastructure change)

```
                   ┌────────────────────────────────────────────────────┐
                   │   Elastic write-path optimisations — quick wins    │
                   └────────────────────────────────────────────────────┘
```

| # | Optimisation | Today | Proposed | Expected gain |
|---|--------------|-------|----------|---------------|
| **E-1** | **`?refresh=false` on bulk-post** | ES auto-refreshes after every bulk request (= makes docs searchable, costs ~50–200 ms per call) | Add `?refresh=false` for batch loads. Trigger ONE explicit `_refresh` at the very end. | **40–60% off** the `post:` timing bucket on big batches |
| **E-2** | **`?routing=` for daily indices** | All shards receive coordination overhead | `?routing={YYYY-MM-DD}` pins a day's docs to one shard at write time | **10–20% off** post latency for high-doc-count batches |
| **E-3** | **HTTP keep-alive / connection pool** | `request()` likely opens a fresh TLS connection per call (50–100 ms TLS handshake each) | `requests.Session()` reused across calls within a run | **Up to 100 ms off every call after the first** — biggest win for slice 1 (many small calls) |
| **E-4** | **Pre-created index template + mapping** | Auto-mapping runs on first doc per index, occasionally produces wrong types (`.keyword` footgun documented in slice 2 reality doc) | Ensure `sg-cf-events-*` template exists at `health` time; create if missing | Eliminates the auto-detect cost AND eliminates a known bug class |
| **E-5** | **Bulk-post body size cap with auto-split** | Single bulk per day — could exceed 100 MB for very busy days | Split at ~10 MB per request (ES recommends 5–15 MB) | Prevents ES out-of-memory rejections on edge cases; future-proofs scale |
| **E-6** | **`_update_by_query` with `terms` filter for manifest flips** | Currently flips one etag at a time across N HTTP calls in slice 2 — this is the `mark:` cost in the timing trace | Single `_update_by_query` with `{"terms": {"etag": [list of N etags]}}` flips all at once | **N× speedup on manifest update** — for the 50-file batch, 50 calls collapse to 1 |
| **E-7** | **Bulk-post `?timeout=` and `?wait_for_active_shards=1`** | Default = wait for primary, can stall on yellow cluster | Explicit timeout 30s, primary-only acks | Defensive; prevents single-replica yellow-cluster stalls |

### Estimated combined impact on the consolidate path

```
   Before any ES optimisation (consolidation alone):  ~660 ms wall time
   After E-1 (refresh=false):                         ~520 ms
   After E-1 + E-3 (keep-alive):                      ~430 ms
   After E-1 + E-3 + E-6 (terms _update_by_query):    ~330 ms

   Compared to today's per-file pipeline (~9.4 sec for 21 files):
     = ~28× speedup, not the originally projected ~14×
```

### What's NOT possible (flagged for honesty)

| | Why not |
|---|---------|
| **Batch S3 GetObject** | AWS S3 has no batch-get API; one GetObject per object is the only path. This is the primary motivation for consolidation in the first place. Future workaround: S3 Select on a manifest file, but that's a separate pattern (and only useful for partial reads). |
| **Parallel S3 fetches** | Possible but adds complexity (boto3 thread-pool, error handling). **Marked as v0.1.102 follow-up.** Architect's instinct: consolidation removes the per-file count enough that parallel fetch becomes a v1.5 nice-to-have, not a v1 essential. |
| **HTTP/2 pipelining to ES** | Elastic 8.13 does not enable HTTP/2 by default. Out of scope. |

### Where these optimisations live in the code

The `Inventory__HTTP__Client` class already exists and is reused by slices 1, 2, and (now) consolidate. **All E-1 through E-7 changes go into that single class.** Existing callers gain the wins automatically. New optional parameters on `bulk_post_with_id`:

```python
def bulk_post_with_id(self,
                      base_url   : str               ,
                      username   : str               ,
                      password   : str               ,
                      index      : str               ,
                      docs       : Type_Safe__List   ,
                      id_field   : str   = 'etag'    ,
                      # NEW (all default to existing behaviour):
                      refresh    : bool  = True      ,   # E-1; pass False during batch loads
                      routing    : str   = ''        ,   # E-2; pass YYYY-MM-DD for daily indices
                      max_bytes  : int   = 0         ,   # E-5; 0 = no split, >0 = auto-split threshold
                     ) -> Tuple[int, int, int, int, str]:
```

Tests gain a new in-memory subclass method `posted_with()` that records `refresh`, `routing`, `max_bytes` so we can assert callers use them correctly.

---

## S3 reorganisation *(NEW — v2 §)*

Decision #5 introduces a `lets/` prefix for our outputs. The source-side `cloudfront-realtime/` prefix remains because **Firehose owns it** — we do not control where Firehose writes. So the reorganisation is one-sided: we add the `lets/` workspace; we do not move Firehose's drops.

### Two-part work

```
   Part A — additive (this slice)
   ──────────────────────────────
   ✓ Define the lets/ workspace structure (decision #5 above)
   ✓ All NEW writes (consolidate output) go to lets/raw-cf-to-consolidated/
   ✓ All NEW reads (events load --from-consolidated) read from lets/
   ✓ Source reads (cloudfront-realtime/) untouched — no breaking change
   ✓ Tests for this work go into the consolidate package only

   Part B — refactor (later, NOT in this slice)
   ─────────────────────────────────────────────
   ✗ Refactor the 58 hardcoded "cloudfront-realtime" strings across 14 files
     to read from a typed primitive (Safe_Str__CF__Source__Prefix) with a
     central default.  Today: hardcoded literals.  Tomorrow: one constant +
     CLI override + env var.  This is a refactor task that benefits all
     three slices but blocks none of them.
```

**Crucial:** Part B is **not in this slice's scope.** The 58 occurrences are tested code paths — refactoring them is a separate PR with its own QA cycle. The Architect explicitly defers it to keep this slice tight and avoid coupling the consolidation feature to a code-cleanup task. (See `07__s3-reorganisation.md` — Sonnet to expand with the inventory of files to touch and the proposed Safe_Str primitive.)

### Firehose destination question (deferred)

The user raised whether to also rename Firehose's destination from `cloudfront-realtime/` to something under `lets/`. This is **not** a code change — it's an AWS console / CDK change to the Firehose delivery stream. Architect's recommendation: **keep Firehose where it is for now.** Reasons:

1. The S3 keys are timestamp-immutable — renaming the prefix would require re-creating the delivery stream with downtime risk.
2. The 58 hardcoded references in tests are golden fixtures with real-world filenames; renaming the live prefix would invalidate them.
3. The `lets/` workspace doesn't *need* to own the source — it owns the **outputs** of LETS workflows. Source data lives wherever it naturally lives.

A cleaner future-state question for the v0.1.102+ window: should Firehose write under `lets/raw-cf/` from day one, with everything else as a derivative? My instinct is yes for greenfield buckets but we shouldn't migrate the existing one until there's a separate operational reason to.

---

## LETS workflow taxonomy *(NEW — v2 §)*

The user's observation is right: **consolidate is one of three workflow types** that can sit on the LETS principle. Naming them now creates a coherent vocabulary for future slices.

```
                     ┌─────────────────────────────────────────┐
                     │         LETS Workflow Taxonomy          │
                     └─────────────────────────────────────────┘

   ┌────────────────────────┬──────────────────────────────────────────────┐
   │  TYPE                  │  EFFECT ON DATA                              │
   ├────────────────────────┼──────────────────────────────────────────────┤
   │                        │                                              │
   │  📦  CONSOLIDATE       │  many small immutable units → one bigger     │
   │      (this slice)      │  fewer files, same total bytes (or smaller) │
   │                        │  shape preserved per-record                  │
   │                        │                                              │
   │      ─────────         │                                              │
   │                        │                                              │
   │  🗜️   COMPRESS          │  records → aggregations / rollups           │
   │      (future)          │  fewer records, less detail                  │
   │                        │  shape changes — schema becomes denser       │
   │                        │  examples: hourly buckets, top-N URIs/day,   │
   │                        │  daily traffic summary, cardinality estimates│
   │                        │                                              │
   │      ─────────         │                                              │
   │                        │                                              │
   │  📈  EXPAND            │  one record → many derivatives               │
   │      (future)          │  more artefacts, more detail                 │
   │                        │  examples: per-event screenshots,            │
   │                        │  per-flow mitm replays, per-URI HAR pulls,   │
   │                        │  graph derivations                           │
   │                        │                                              │
   └────────────────────────┴──────────────────────────────────────────────┘
```

### All three share the same scaffolding

What's common across all three workflow types — and therefore what `Consolidate__Loader` is the first instance of, not the only one:

```
   ┌──────────────────────────────────────────────────────────────────┐
   │   The shared scaffolding (extracted from Consolidate__Loader)    │
   │                                                                  │
   │   1. Read lets-config.json at compat-region root                 │
   │   2. Resolve work queue (from inventory, from manifest, from     │
   │      previous workflow output, from S3 listing, …)               │
   │   3. Loop: per-input → transform → write output                  │
   │   4. Persist output to a new compat region                       │
   │   5. Write per-day manifest sidecar                              │
   │   6. Index manifest doc into Elastic                             │
   │   7. Flip a "this was processed" flag on the source              │
   │   8. Record one Schema__Pipeline__Run journal entry              │
   │                                                                  │
   │   The only thing that varies between workflow types is:          │
   │     - the "transform" function (parser, aggregator, expander)    │
   │     - the input/output schema pair                               │
   │                                                                  │
   └──────────────────────────────────────────────────────────────────┘
```

### Concrete future workflows worth flagging

| Workflow | Type | Input | Output | Why |
|----------|------|-------|--------|-----|
| `consolidate cf-events` | 📦 | Firehose `.gz` files | `events.ndjson.gz` per day | This slice |
| `consolidate mitm-flows` | 📦 | mitmproxy session dumps | `flows.ndjson.gz` per session | Generalises to per-session work units |
| `consolidate playwright-sessions` | 📦 | per-page artefact bundles | `session.ndjson.gz` + `assets/` | HARs + screenshots + traces in one consolidated form |
| `compress cf-hourly-rollup` | 🗜️ | consolidated events | `hourly-rollup.ndjson` | Pre-aggregated panels for fast Kibana loads |
| `compress cf-daily-summary` | 🗜️ | consolidated events | one summary doc / day | The `sg-send report` Tier 3 command, productised |
| `expand mcp-tool-replay` | 📈 | tool-call log | replay artefacts (request/response/state delta) per call | Investigation-time forensics |
| `expand cf-event-screenshot` | 📈 | event with `404` status | playwright screenshot of the URI at that timestamp | Debug-aid for production weirdness |

**This is not a roadmap commitment.** It's a vocabulary for naming future briefs. v0.1.101 ships consolidate-cf-events. Subsequent briefs will reference this taxonomy.

(See `09__lets-workflow-taxonomy.md` — Sonnet to expand into a longer treatment with examples for each.)

---

## Trigger model roadmap *(NEW — v2 §)*

Today every LETS verb runs because a human typed it. That's fine for v0.1.101 (the one human is Dinis, and the cadence is "when I want to look at the data"). But the architecture needs to anticipate **scheduled** and **event-triggered** execution because that's where this is heading.

```
                    ┌────────────────────────────────────────┐
                    │       Trigger Model Maturity Path      │
                    └────────────────────────────────────────┘

      Today (v0.1.101)              Soon (v0.1.103+)         Eventually
      ────────────────              ─────────────────         ──────────
      ┌─────────────┐                ┌─────────────┐         ┌─────────────┐
      │   Manual    │                │  Scheduled  │         │  Triggered  │
      │     CLI     │                │    cron     │         │  (S3 event) │
      │             │                │             │         │             │
      │  Operator   │                │  GitHub     │         │  S3 PUT     │
      │  types:     │                │  Actions    │         │  → SNS      │
      │             │                │  schedule:  │         │  → SQS      │
      │  sp el lets │                │    daily    │         │  → Lambda   │
      │  cf consol- │                │    @ 02:00  │         │  invokes    │
      │  idate load │                │             │         │  same       │
      │             │                │  Calls same │         │  service    │
      │             │                │  service    │         │  class      │
      │             │                │  class      │         │             │
      └─────────────┘                └─────────────┘         └─────────────┘
            │                              │                       │
            └──────────┬───────────────────┴───────────────────────┘
                       │
                       ▼
        ┌─────────────────────────────────────────────┐
        │   Same Consolidate__Loader class is the     │
        │   target in all three trigger modes.        │
        │                                             │
        │   That's why decision #11 (no boto3 outside │
        │   S3__* boundaries) and the three-tier      │
        │   architecture matter — Consolidate__Loader │
        │   has to be invokable from anywhere.        │
        └─────────────────────────────────────────────┘
```

### What this means for v0.1.101

**Nothing tactical.** The trigger model is enabled by getting the architecture right today, not by writing trigger code. Specifically:

1. **`Consolidate__Loader` must be a pure Type_Safe service class** with no Typer / no Console / no Rich dependency in the class itself. The Console output is in the Typer wrapper; the service is callable from Lambda or GH Actions tomorrow with the same signature.

2. **`Consolidate__Loader.load(request: Schema__Consolidate__Load__Request) -> Schema__Consolidate__Load__Response`** is the trigger contract. As long as that signature stays clean, every trigger surface (CLI / cron / S3 event) constructs a Request, calls `.load()`, and persists the Response.

3. **The shared `Call__Counter` and `Pipeline__Runs__Tracker`** remain valid in serverless contexts — they're `Type_Safe` classes with no global state.

4. **The `lets-config.json` at the compat-region root** becomes the *coordination point* for triggered execution: a Lambda triggered by an S3 event under `lets/raw-cf-to-consolidated/` reads the config to know which workflow class to instantiate.

(See `10__trigger-model-roadmap.md` — Sonnet to expand into the concrete Lambda + cron architecture for v0.1.103+.)

### What this means for the orchestrator (v0.1.102)

The `SG_Send__Orchestrator` class becomes the **trigger-target template** for the manual case. Its `sync()` method is the same shape that a cron-triggered `SG_Send__Daily__Sync__Lambda` will call. Designing the orchestrator now with that shape in mind costs nothing extra and saves rewriting it later.

---

## What's NOT in this slice (deferred)

- **Append-mode consolidation** — if a new `.gz` arrives after consolidation, v1 re-runs the full date. Append is a v2 feature; for SGraph-Send the Firehose drops are delayed enough that an "end-of-day cron at 02:00 UTC" makes re-run-the-day acceptable.
- **Per-hour granularity** — flag exists (`--granularity hour`) but the day-grain default is the only path tested in v1.
- **Parquet output** — NDJSON.gz only.
- **Multi-source registry** — consolidate is hardcoded to CF realtime logs, same as slice 2.
- **`SG_Send__Orchestrator`** — that's v0.1.102. This slice's `events load --from-consolidated` flag is the seam the orchestrator will use.
- **Read-side `sp el lets cf runs`** — the `Pipeline__Runs__Tracker` is being written to by this slice; the read CLI is a later (small) follow-up.
- **The 58-occurrence `cloudfront-realtime` literal refactor** — Part B above. Separate PR, separate slice.
- **Firehose destination rename** — see "Firehose destination question" above. Out of scope.
- **Compress / Expand workflow types** — taxonomy named in this brief; concrete briefs are v0.1.103+.
- **Scheduled / triggered execution** — architecture enabled by this slice's design choices; concrete cron/Lambda code is v0.1.103+.
- **Parallel S3 fetches inside consolidate** — flagged as a v0.1.102 follow-up if consolidation wall-time becomes a concern at scale.

---

## Implementation phase outline (Sonnet to expand into `06__implementation-phases.md`)

Six phases, each PR-sized, each ending with a green test suite or working demo. Total estimated effort ≈ 6–7 days for a single Dev (slightly larger than v1 estimate because of the new ES optimisations in `Inventory__HTTP__Client` — roughly 1 extra day).

```
   Phase 1 — Type_Safe foundations (1 day)
     Same as v1.  Adds:
       Schema__Lets__Config (the lets-config.json shape — decision #5)
       Schema__Consolidated__Manifest (the per-day sidecar)
       Safe_Str__Lets__Workflow__Type (consolidate / compress / expand)
       Enum__Pipeline__Verb gains CONSOLIDATE
     Demo: pytest green

   Phase 2 — S3 write boundary + Inventory__HTTP__Client optimisations (1.5 days)
     S3__Object__Writer + S3__Object__Writer__In_Memory  (as before)
     Inventory__HTTP__Client gains optional refresh/routing/max_bytes params
       (E-1, E-2, E-5 from §"Elastic optimisations")
     Inventory__HTTP__Client gains a requests.Session() (E-3 keep-alive)
     Inventory__HTTP__Client gains terms-filter _update_by_query path (E-6)
     All existing callers: NO behaviour change (defaults preserve current
       behaviour); ~10 new tests assert the new defaults work as expected
     Demo: pytest green; existing 351 tests still green

   Phase 3 — NDJSON consolidation core + lets-config.json read/write (1 day)
     NDJSON__Writer / NDJSON__Reader        (as before)
     Manifest__Builder (per-day Schema__Consolidated__Manifest)
     Lets__Config__Reader (validates a compat-region's config, refuses
       reads from incompatible regions — decision #5b)
     Lets__Config__Writer (writes config at first use of a region)
     Demo: pytest green

   Phase 4 — Consolidate__Loader orchestrator (1.5 days)
     Same as v1 plus:
       reads lets-config.json before any write (creates it if missing)
       writes manifest.json sidecar at lets/raw-cf-to-consolidated/{YYYY/MM/DD}/
       writes events.ndjson.gz at same prefix
       _update_by_query uses terms filter (E-6)
       bulk-post uses refresh=false (E-1)
     Demo: pytest green; ~30+ unit tests

   Phase 5 — events load --from-consolidated mode (1 day)
     Same as v1 plus:
       reads lets-config.json first; refuses incompat region with clear error
       single bulk-post with refresh=false + routing={date} (E-1, E-2)
       single _update_by_query with terms filter (E-6)
     Demo: pytest green; events load --from-consolidated wall-time on a 21-file
       day < 0.5 second (vs ~9 sec today, was ~1 sec in v1 before
       ES optimisations)

   Phase 6 — CLI + dashboard + reality doc (0.5–1 day)
     Same as v1
     Adds: sp el lets cf consolidate verify <date> reads lets-config + manifest
       and reports drift / mismatches
     Demo: end-to-end against a real Ephemeral Kibana stack
```

**Phase 0** (before Phase 1, ~1 hour): Sonnet expands docs `01–10` of this brief from the architect's grounding docs into the existing 6-doc brief shape used by slices 1 & 2 (now expanded to 10 docs to cover the new sections). Architect reviews. **No code is written until docs 01–10 are in place.**

---

## Cross-references

- **Architect grounding**: `00__cloudfront-lets-architecture-review.md`, `00b__consolidation-lets-pattern.md` (this folder)
- **Slice 1 (inventory)**: `team/comms/briefs/v0.1.99__sp-el-lets-cf-inventory/`
- **Slice 2 (events)**: `team/comms/briefs/v0.1.100__sp-el-lets-cf-events/`
- **Phase A diagnostics**: `Call__Counter`, `Step__Timings`, `Progress__Reporter`
- **Phase B journal**: `runs/` package, `Pipeline__Runs__Tracker`
- **Reality docs**: `team/roles/librarian/reality/v0.1.31/{10,11}__lets-cf-{inventory,events}.md`
- **CLI/FastAPI duality**: `team/comms/briefs/v0.1.72__sp-cli-fastapi-duality.md`
- **Project rules**: `.claude/CLAUDE.md`

---

## Sign-off checklist (Architect → Dev handoff)

Before Sonnet starts Phase 1, this checklist must be all-checked:

- [ ] All 15 locked decisions in this README are accepted
- [ ] All 7 ES optimisation items (E-1 through E-7) are accepted
- [ ] The S3 reorganisation (Part A only, Part B deferred) is accepted
- [ ] The LETS workflow taxonomy (consolidate / compress / expand) is accepted as future-vocabulary, not roadmap-commitment
- [ ] The trigger model roadmap is accepted as architecture-shaping, not v0.1.101 deliverable
- [ ] Branch created from `dev`: `claude/lets-cf-consolidate-{session-id}`
- [ ] Architect grounding docs 00 + 00b are in this folder and have been read by the Dev session
- [ ] Sonnet has expanded docs 01–10 of this brief and an Architect review has approved them
- [ ] No code in `sgraph_ai_service_playwright__cli/elastic/lets/cf/consolidate/` exists yet (Phase 0 is docs-only)

---

## Status updates

| Date | Note |
|------|------|
| 2026-04-27 | v1 brief filed by Architect. |
| 2026-04-27 | v2 — incorporated Dinis's refinements: lets-config.json at folder root (replaces filename versioning), S3 reorganisation under `lets/`, ES optimisations section, future-work taxonomy (consolidate/compress/expand), trigger model roadmap. Awaiting Sonnet Dev pickup of Phase 0 (expand docs 01–10). |
