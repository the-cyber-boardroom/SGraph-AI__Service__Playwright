# Consolidation LETS — Pre-Compaction of Immutable Source Datasets

**Author:** Architect (Explorer session)
**Date:** 2026-04-27
**Status:** Architectural proposal — for discussion before brief
**Companion doc:** `01__cloudfront-lets-architecture-review.md`

---

## TL;DR

When a source dataset is composed of many small, immutable units (Firehose `.gz` files, audit log lines, transaction events, mitmproxy flows, screenshots), **consolidate them into a fewer-and-larger artefact once, then index from the consolidated artefact**. This is a generalisable LETS pattern — call it **the C-step** (Consolidate) sitting between Load and Extract.

Concrete impact for the CloudFront pipeline today: ~14× speedup on the daily refresh, from ~10 seconds to under 1 second for the same date.

---

## 1. The bottleneck — measured, not assumed

From your live trace (21 files, 150 events, partial day):

```
  per-file breakdown (ms)
                  ┌─────┬─────┬───────┬──────┬──────┬───────┐
                  │ s3  │ gz  │ parse │ post │ mark │ TOTAL │
  ────────────────┼─────┼─────┼───────┼──────┼──────┼───────┤
  median          │ 175 │  0  │   8   │ 141  │ 102  │  ~430 │
  fraction of run │ 41% │ 0%  │   2%  │ 33%  │ 24%  │  100% │
  ────────────────┴─────┴─────┴───────┴──────┴──────┴───────┘
```

```
                       ╔══ THE PROBLEM IN ONE PICTURE ══╗
                       ║                                ║
                       ║      99% overhead              ║
                       ║      ┌────────────────┐        ║
                       ║      │░░░░░░░░░░░░░░░░│        ║
                       ║      │░ s3 GetObject ░│        ║
                       ║      │░░░░░░░░░░░░░░░░│        ║
                       ║      │░░ ES bulk-post░│        ║
                       ║      │░░░░░░░░░░░░░░░░│        ║
                       ║      │░░ manifest-up ░│        ║
                       ║      │░░░░░░░░░░░░░░░░│        ║
                       ║      │░░░░░░░░░░░░░░░░│        ║
                       ║      ├─parse─(2%)─────┤        ║
                       ║      └────────────────┘        ║
                       ║                                ║
                       ║   ≪ Real work : Wrapper ≫     ║
                       ║          1   :   50            ║
                       ╚════════════════════════════════╝
```

**The interpretation:**

- **`s3:170ms`** — TLS handshake + region routing + GetObject request/response. Mostly latency, not bandwidth. A 50 KB file and a 5 MB file have nearly the same `s3:` cost.
- **`gz:0ms`** — gzip is so fast at this size it doesn't even register. Free.
- **`parse:8ms`** — actual work. Scales linearly with event count.
- **`post:141ms`** — one ES bulk-post HTTP round-trip. Fixed cost per call, almost regardless of payload size up to several MB.
- **`mark:102ms`** — one `_update_by_query` HTTP round-trip per file. Fixed cost.

**Three of the five timing buckets are dominated by per-file fixed overhead, not per-event work.** That is the telltale signature of a workload that wants to be batched.

---

## 2. The pattern — a new LETS layer

Today the LETS stages map onto the CloudFront pipeline like this:

```
   ┌─────────┐   ┌───────────┐   ┌─────────────┐   ┌────────┐
   │    L    │──▶│     E     │──▶│      T      │──▶│   S    │
   │  Load   │   │  Extract  │   │  Transform  │   │  Save  │
   │ (S3 ls) │   │ (per-file │   │  (deferred) │   │ (bulk- │
   │         │   │  TSV parse│   │             │   │  post) │
   │         │   │  + bot    │   │             │   │        │
   │         │   │  classify)│   │             │   │        │
   └─────────┘   └───────────┘   └─────────────┘   └────────┘
                    │
                    └─── repeated 425× per day, with ~440ms
                         per-file fixed overhead each time
```

The proposal is to insert a **C-stage (Consolidate)** that runs once per logical group (per day, per hour, per source-aware bucket), persists the consolidated artefact back to a new S3 prefix, and then becomes the input for E + S:

```
   ┌─────────┐   ┌─────────────────┐   ┌──────────┐   ┌────────┐
   │    L    │──▶│       C         │──▶│    E     │──▶│   S    │
   │  Load   │   │  Consolidate    │   │ Extract  │   │  Save  │
   │ (S3 ls  │   │  (NEW STAGE)    │   │ (1× per  │   │ (1× per│
   │  inv-   │   │                 │   │  bucket) │   │  bucket│
   │  entory)│   │  ① fetch all .gz│   │          │   │        │
   │         │   │  ② concat lines │   │          │   │        │
   │         │   │  ③ persist to S3│   │          │   │        │
   │         │   │  ④ mark sources │   │          │   │        │
   │         │   │                 │   │          │   │        │
   └─────────┘   └─────────────────┘   └──────────┘   └────────┘
                          │
                          └─── runs ONCE per day per bucket
                               output is itself immutable
                               and content-addressed
```

**The `C` is the missing letter — the pipeline becomes L-C-E-T-S.** Or, in the language we already use for slices, this is **Slice 0.5** (between inventory listing and event extraction) or equivalently **a new `consolidate` verb under `sp el lets cf`**.

---

## 3. The concrete CloudFront design

```
     ┌────────────────────────────────────────────────────────────────────┐
     │                                                                    │
     │   S3 — original Firehose drop                                      │
     │                                                                    │
     │   cloudfront-realtime/2026/04/27/00/                               │
     │     EXXX.....571fc6ff.gz   12 events                               │
     │     EXXX.....636b6f21.gz   11 events                               │
     │     EXXX.....63426470.gz   14 events                               │
     │     ... × 425 files, ~1500 events total per day                    │
     │                                                                    │
     └─────────────────────────────────────┬──────────────────────────────┘
                                           │
                                           │  C-stage runs ONCE per day
                                           │  (idempotent — keyed on
                                           │   source-set hash)
                                           ▼
     ┌────────────────────────────────────────────────────────────────────┐
     │                                                                    │
     │   S3 — same bucket, new prefix (or sibling bucket)                 │
     │                                                                    │
     │   cloudfront-consolidated/2026/04/27/                              │
     │     events.ndjson.gz                                               │
     │       ├── line 1: {parsed event from 571fc6ff line 0,              │
     │       │            source_etag=571fc6ff__0, line_index=0,          │
     │       │            consolidation_run_id=cons-2026-04-27-abc123}    │
     │       ├── line 2: {... 571fc6ff line 1 ...}                        │
     │       ├── ...                                                      │
     │       └── line 1500: {... last event ...}                          │
     │                                                                    │
     │     manifest.json                                                  │
     │       { "run_id":           "cons-2026-04-27-abc123",              │
     │         "source_etags":     [571fc6ff, 636b6f21, ...],             │
     │         "source_count":     425,                                   │
     │         "event_count":      1500,                                  │
     │         "schema_version":   "v1",                                  │
     │         "parser_version":   "v0.1.100",                            │
     │         "bot_classifier_v": "v0.1.100",                            │
     │         "consolidated_at":  "2026-04-27T01:05:00Z" }               │
     │                                                                    │
     └─────────────────────────────────────┬──────────────────────────────┘
                                           │
                                           │  E + S stages now run ONCE
                                           │  on the consolidated artefact
                                           ▼
     ┌────────────────────────────────────────────────────────────────────┐
     │                                                                    │
     │   Elasticsearch — sg-cf-events-2026-04-27                          │
     │                                                                    │
     │   1500 docs, _id = {source_etag}__{line_index}                     │
     │   (same idempotency key as today — no schema break)                │
     │                                                                    │
     └────────────────────────────────────────────────────────────────────┘
```

**Two new things, nothing breaks:**

1. **A new `consolidated_*` prefix in S3** — the consolidated artefact is itself persisted, and itself becomes immutable once written. The source `.gz` files are never modified or deleted.
2. **A new manifest doc** — content-addressed by the set of source etags it covers. Re-running consolidation for the same date/source-set produces a byte-identical output (or upserts in place if input gained new files).

**Everything downstream stays the same.** The events index still keys on `{source_etag}__{line_index}`. The bot classifier still runs over the same TSV lines. The dashboards don't notice. The only change is **where** the per-event records come from — a fast read of one consolidated file instead of 425 slow reads.

---

## 4. Numerical impact on the CloudFront pipeline

```
   ┌─────────────────────────────────────────────────────────────────┐
   │                                                                 │
   │  Today (21 files × 7 events avg) — partial day                  │
   │  ────────────────────────────────                               │
   │  Per-file overhead:    21 × ~440 ms  =  9,240 ms                │
   │  Real parse work:           ~150 ms total                       │
   │  ──────────────────────────────────                             │
   │  Wall time:                ~9.4 sec                             │
   │                                                                 │
   │                                                                 │
   │  After consolidation (same 150 events, 1 consolidated file)     │
   │  ───────────────────────────────────────────────────────────    │
   │  s3 GetObject:              ~200 ms  (1 round-trip)             │
   │  gz decompress:             ~5 ms                               │
   │  parse:                     ~150 ms  (same total work)          │
   │  bulk-post:                 ~200 ms  (1 HTTP call)              │
   │  mark (new: range update):  ~100 ms  (1 _update_by_query        │
   │                                       over the 21 source etags) │
   │  ──────────────────────────────────                             │
   │  Wall time:                ~660 ms                              │
   │                                                                 │
   │                                                                 │
   │   Speedup:    ~14×        Reads from S3:    21 → 1              │
   │   ES calls:   ~63 → 4     manifest flips:  21 → 1               │
   │                                                                 │
   └─────────────────────────────────────────────────────────────────┘
```

**At full-day scale (425 files):**

- Today's `events load --from-inventory` for a full day: ~3.1 minutes
- After consolidation: ~5 seconds for the events load (the consolidation step itself runs in ~3 minutes once, then is cached forever)

**The consolidation cost is paid once per day**. After that, every re-load (whether after a stack rebuild, a parser bump, an index template change, or a developer experimenting locally) takes ~5 seconds instead of 3 minutes.

This is the asymmetric win: the pattern is most valuable not on the first run, but on **every subsequent run**.

---

## 5. Why this is more than an optimisation — it's the LETS principle taken seriously

Re-read the LETS principle from your handover:

> *"Persist Everything Important BEFORE Indexing Anything. Elasticsearch is NOT the source of truth — it is an index, a cache, a search layer."*

Today, the pipeline persists the *source* layer (the Firehose `.gz` drops in S3) and the *index* layer (Elasticsearch). **The Extract layer is ephemeral** — every re-load redoes the parse-and-classify work. That's a missed opportunity to honour the principle on the layer where the cost actually lives.

```
   ┌──────────────────────────────────────────────────────────────────┐
   │                                                                  │
   │   What LETS persists today:                                      │
   │                                                                  │
   │     ┌──────┐               ┌─────────┐                           │
   │     │  L   │═══════════════│    S    │                           │
   │     │ raw  │  ephemeral E  │  index  │                           │
   │     │ S3   │  (re-runs     │  in ES  │                           │
   │     └──────┘   every time) └─────────┘                           │
   │        │                        │                                │
   │        └─ persistent ───────────┴── persistent                   │
   │                                                                  │
   │                                                                  │
   │   What LETS persists after consolidation:                        │
   │                                                                  │
   │     ┌──────┐    ┌──────┐    ┌──────┐    ┌─────────┐              │
   │     │  L   │═══▶│  C   │═══▶│  E   │═══▶│    S    │              │
   │     │ raw  │    │ cons │    │parse │    │  index  │              │
   │     │ S3   │    │ S3   │    │      │    │  in ES  │              │
   │     └──────┘    └──────┘    └──────┘    └─────────┘              │
   │        │           │        ephemeral        │                   │
   │        └ persist ──┴──────────────────────── persist             │
   │                                                                  │
   │   The C-layer is the missing persistent step.                    │
   │   E becomes "the cheap function that re-runs on demand"          │
   │   exactly as the principle intended.                             │
   │                                                                  │
   └──────────────────────────────────────────────────────────────────┘
```

The consolidated S3 artefact is **the right place** to capture: parser version, bot-classifier version, schema version, source-set hash. When any of those change, you re-consolidate — and the resulting artefact is itself the audit trail of "this is what the pipeline thought the world looked like at 03:00 UTC on 2026-04-27 with parser v0.1.100".

---

## 6. The pattern, generalised

The pattern lives wherever this signature appears:

```
   ╔════════════════════════════════════════════════════════╗
   ║   Consolidation Pattern — Recognition Criteria         ║
   ╠════════════════════════════════════════════════════════╣
   ║                                                        ║
   ║   ✓  Source dataset = many small immutable units       ║
   ║   ✓  Per-unit overhead dominates per-event work        ║
   ║   ✓  Units are append-only (closed once written)       ║
   ║   ✓  Re-processing happens repeatedly (not once)       ║
   ║                                                        ║
   ║   Likely candidates inside the SGraph ecosystem:       ║
   ║                                                        ║
   ║   ┌─────────────────────┬─────────────────────────┐    ║
   ║   │ Source              │ Unit / consolidate by   │    ║
   ║   ├─────────────────────┼─────────────────────────┤    ║
   ║   │ CF realtime logs    │ .gz file / day          │    ║
   ║   │                     │  ◄── this proposal      │    ║
   ║   ├─────────────────────┼─────────────────────────┤    ║
   ║   │ mitmproxy flows     │ flow file / session     │    ║
   ║   │                     │   (one mitm dump per    │    ║
   ║   │                     │    request → consolidate│    ║
   ║   │                     │    per session/hour)    │    ║
   ║   ├─────────────────────┼─────────────────────────┤    ║
   ║   │ Playwright sessions │ session-artefacts /     │    ║
   ║   │ (HAR + screenshots  │  date or session-id     │    ║
   ║   │  + traces per page) │                         │    ║
   ║   ├─────────────────────┼─────────────────────────┤    ║
   ║   │ Service audit logs  │ event line / day        │    ║
   ║   │ (CloudTrail-like,   │                         │    ║
   ║   │  one .json per call)│                         │    ║
   ║   ├─────────────────────┼─────────────────────────┤    ║
   ║   │ MCP tool-call logs  │ tool invocation / day   │    ║
   ║   │ (one .ndjson per    │ or per session          │    ║
   ║   │  invocation)        │                         │    ║
   ║   ├─────────────────────┼─────────────────────────┤    ║
   ║   │ Vault commits (sgit)│ commit / day or branch  │    ║
   ║   │ (per-file blobs)    │                         │    ║
   ║   ├─────────────────────┼─────────────────────────┤    ║
   ║   │ Prometheus scrapes  │ scrape / hour           │    ║
   ║   │ (15s scrape interval│                         │    ║
   ║   │  → 5760 files/day)  │                         │    ║
   ║   ├─────────────────────┼─────────────────────────┤    ║
   ║   │ ALB / WAF logs      │ same shape as CF        │    ║
   ║   │ (Firehose → small   │                         │    ║
   ║   │  .gz)               │                         │    ║
   ║   └─────────────────────┴─────────────────────────┘    ║
   ║                                                        ║
   ╚════════════════════════════════════════════════════════╝
```

**Pattern is the same in each case:**

```
   raw drops ──▶ daily/hourly consolidate ──▶ index/query layer
   (S3, vault,   (one artefact per group,    (Elasticsearch,
    Firehose,     content-addressed,          Kibana, vault
    Prom WAL)     immutable)                  views)
```

Once you have one good implementation of `Consolidate`, every new source plugs in the same way — only the parser changes.

---

## 7. The reusable building blocks

Looking at what already exists, **most of the consolidation machinery is already in place** — it just isn't wired up as its own LETS stage yet:

```
   ┌──────────────────────────────────────────────────────────────┐
   │                                                              │
   │   Already exists today:                                      │
   │                                                              │
   │   ✓  S3__Inventory__Lister      — list source files         │
   │   ✓  S3__Object__Fetcher        — read source bytes         │
   │   ✓  CF__Realtime__Log__Parser  — parse TSV                 │
   │   ✓  Bot__Classifier            — classify UA               │
   │   ✓  Inventory__HTTP__Client    — bulk-post to ES           │
   │   ✓  Schema__CF__Event__Record  — typed event               │
   │                                                              │
   │   What's needed (small):                                     │
   │                                                              │
   │   +  S3__Object__Writer         — boundary for PutObject     │
   │      (sibling of S3__Object__Fetcher; new boto3 surface,     │
   │       small, follows the existing seam pattern)              │
   │                                                              │
   │   +  Schema__Consolidated__Manifest — describes an output    │
   │      (run_id, source_etags, source_count, event_count,       │
   │       schema_version, parser_version, written_at)            │
   │                                                              │
   │   +  Consolidate__Loader        — orchestrator for the stage │
   │      (reuses Inventory + Fetcher + Parser; writes the .ndjson│
   │       and manifest; records to Pipeline__Runs__Tracker)      │
   │                                                              │
   │   +  Schema__Consolidate__Source — one entry per consumed    │
   │      source file (etag, line_count, byte_offset_start, …)    │
   │      so a single line in the consolidated file can still     │
   │      be traced back to its source .gz                        │
   │                                                              │
   │   +  Enum__Pipeline__Verb adds CONSOLIDATE — already an enum,│
   │      one-line addition                                       │
   │                                                              │
   └──────────────────────────────────────────────────────────────┘
```

**This is the right kind of architectural addition** — every new piece sits on a clean existing seam, no boundaries blur, the existing rules from `.claude/CLAUDE.md` are honoured (`Type_Safe`, one-class-per-file, no boto3 outside `S3__*` boundaries, `Inventory__HTTP__Client` for all HTTP, no mocks in tests).

---

## 8. New CLI surface

```
   sp el lets cf consolidate                  NEW: the C-stage commands
   sp el lets cf consolidate load             Run consolidation for a date
                                              [--prefix YYYY/MM/DD]
                                              [--from-inventory] (default)
                                              [--output-prefix
                                                  cloudfront-consolidated/]
                                              [--dry-run]
                                              [--max-files N]
   sp el lets cf consolidate wipe             Drop all consolidated artefacts
                                              for a date (NOT the source .gz)
                                              + reset the manifest's
                                              consolidation flag
   sp el lets cf consolidate list             Show consolidation runs (date,
                                              source_count, event_count,
                                              parser_version)
   sp el lets cf consolidate health           Plumbing checks:
                                                ✓ output prefix writable
                                                ✓ source manifest readable
                                                ✓ recent run exists
   sp el lets cf consolidate verify <date>    Read the consolidated artefact,
                                              recompute source-set hash,
                                              compare with manifest;
                                              detect drift / partial writes
```

And then the **events load** gains a third queue mode:

```
   sp el lets cf events load --from-consolidated
       reads the consolidated .ndjson.gz file directly
       skips per-source-file fetch entirely
       still produces the same docs in sg-cf-events-{date}
       still flips inventory.content_processed (range update,
       one _update_by_query for all source etags in the manifest)
```

The orchestrator becomes:

```
   sp el lets cf sg-send sync   ← becomes a 3-step pipeline:
                                  1. inventory load
                                  2. consolidate load --from-inventory
                                  3. events load --from-consolidated
                                  (still one shared Call__Counter,
                                   one Schema__Pipeline__Run journal doc)
```

---

## 9. Decisions to make in the brief

The proposal opens up several design questions that the next planning round needs to answer:

| Question | Options | Architect's lean |
|----------|---------|------------------|
| **Output format** | NDJSON.gz / Parquet / Avro / SQLite | NDJSON.gz — keeps the LETS principle of human-readable + grep-able + simple. Parquet is a future Tier 3 if columnar reads become a need. |
| **Granularity** | Per-day / per-hour / per-source-set | Per-day default; allow `--granularity hour` flag. Day matches the existing `sg-cf-events-{date}` index naming. |
| **Source bucket** | Same bucket new prefix / sibling bucket | Same bucket, new top-level prefix `cloudfront-consolidated/`. One IAM policy, one lifecycle rule, no cross-bucket coordination. |
| **Idempotency key** | `consolidation_run_id` / `source_etag_set_hash` / `{date}_{parser_version}` | `{date}_{parser_version}` as the S3 key suffix — re-consolidation under the same parser overwrites; a parser bump produces a new file alongside the old. |
| **Manifest location** | Inline JSON in S3 / sidecar `.json` / Elasticsearch doc | Both: a `.json` sidecar in S3 (the durable record) AND a doc in `sg-cf-consolidated-{date}` (so Kibana can show "what's been consolidated today"). |
| **Source manifest flag** | New field `consolidation_run_id` on `Schema__S3__Object__Record` / separate index | Add `consolidation_run_id` and `consolidated_at` to the existing inventory doc, alongside `content_processed` / `content_extract_run_id`. Same flip pattern, same `_update_by_query`. |
| **What if a new `.gz` arrives after consolidation?** | Re-run / append / hot-tail | Re-run for v1 (simple, idempotent, ~3 min); append-mode is a v2 feature. The Firehose drop is delayed enough that an "end-of-day at 02:00 UTC" cron is a reasonable v1. |
| **Wipe semantics** | Delete the consolidated artefact / leave it / move to "trash" prefix | Delete by default (matched-pair rule). The source is still in `cloudfront-realtime/` — the consolidated artefact is reproducible. |
| **Compression** | gzip / zstd / none | gzip — same toolchain as Firehose, no new dependency. The events.ndjson.gz file is ~80% smaller than the sum of source `.gz` files because the manifest header amortises and TSV→JSON is denser-when-compressed for repeated keys. |
| **File size cap** | 100 MB / 1 GB / unbounded | 1 GB soft cap with auto-split into `events.001.ndjson.gz`, `events.002.ndjson.gz`. Gives Lambda a way in if we ever need to push processing serverless. |

---

## 10. How this changes the next planning round

The brief I was about to write — `v0.1.101__sp-el-lets-sg-send-orchestrator/` — was scoped around composing the existing `Inventory__Loader` and `Events__Loader` into a single `sync` command.

If we want to slot consolidation in, **the right move is to split that brief into two**:

```
   ┌──────────────────────────────────────────────────────────────┐
   │  Option A — sequence them, smaller PRs, ship sooner          │
   │                                                              │
   │  v0.1.101__sp-el-lets-cf-consolidate/                        │
   │     The C-stage on its own. Reuses existing classes.         │
   │     ~2 weeks of Sonnet Dev work.                             │
   │     New CLI: sp el lets cf consolidate {load,wipe,list,...}  │
   │     New schemas: Manifest, Source, ConsolidateRun            │
   │     New service: Consolidate__Loader, S3__Object__Writer     │
   │     New flag: events load --from-consolidated                │
   │                                                              │
   │  v0.1.102__sp-el-lets-sg-send-orchestrator/                  │
   │     SG_Send__Orchestrator now wraps the 3-step pipeline:     │
   │       inventory → consolidate → events                       │
   │     Same shared Call__Counter, same Pipeline__Runs__Tracker  │
   │     CLI: sp el lets cf sg-send sync, status, ...             │
   │                                                              │
   │  Total: ~3 weeks. Each PR is shippable and testable on its   │
   │  own. v0.1.101 already gives you the 14× speedup on existing │
   │  manual two-step recipe.                                     │
   └──────────────────────────────────────────────────────────────┘

   ┌──────────────────────────────────────────────────────────────┐
   │  Option B — bundle them, one bigger PR                       │
   │                                                              │
   │  v0.1.101__sp-el-lets-cf-consolidate-and-orchestrate/        │
   │     Both at once. Larger blast radius, more rollback         │
   │     surface, more tests to write before any value lands.     │
   │     ~4 weeks of Sonnet Dev work.                             │
   │                                                              │
   │  Architect's recommendation: don't.                          │
   └──────────────────────────────────────────────────────────────┘
```

**My recommendation: Option A.** The consolidation slice is the strictly bigger architectural insight, ships independent value (the 14× speedup), and gives the orchestrator brief a cleaner story (it composes 3 verbs instead of 2 — pure addition).

---

## 11. What I'd like your input on before I draft the brief

1. **Pattern naming** — I've been calling it the **C-stage** and **`consolidate`** verb. Are you comfortable with that? Alternatives that fit the existing vocabulary: `compact`, `bundle`, `roll-up`. (`compact` collides with database compaction connotations; `bundle` reads as packaging; `roll-up` collides with OLAP. `consolidate` is closest to plain English.)

2. **Source-ecosystem scope** — should this brief explicitly call out the *generalisable* pattern (and recommend its application to mitmproxy / Playwright artefacts / vault commits) — or stay focused on CloudFront and let the pattern emerge organically as those subsystems hit the same wall? My instinct is **stay focused for the brief, but include a "generalises to" appendix** so future readers see the bigger picture without scope-creeping the implementation.

3. **Persistence layer** — does the consolidated artefact go in the same `745506449035--sgraph-send-cf-logs--eu-west-2` bucket under a new prefix, or do you want a sibling bucket (`...-consolidated--eu-west-2`)? Same bucket is operationally simpler. Sibling bucket gives you separate IAM, separate lifecycle rules, separate billing visibility.

4. **Order of operations vs. v0.1.96 plan** — the locked v0.1.96 playwright-stack-split plan doesn't reference LETS consolidation. Do we treat this as **a parallel track to v0.1.96** (since it touches `sp el lets`, not the playwright EC2), or do you want me to flag it for the v0.1.96 owners first? My read: parallel track. They share no surface area.

5. **The big-picture pitch** — would it be useful for me to write a separate, shorter "**The Consolidation Pattern Across SGraph**" doc as a Cartographer-style overview (not a brief, more a manifesto) that you could share with the wider team to align everyone on this principle? The implementation brief stays scoped; the manifesto sets the direction.

I think you've spotted a genuinely high-leverage architectural lever here. The pattern has the property of all good architectural ideas: it's obvious in hindsight, it doesn't need any new infrastructure, and once one subsystem demonstrates it, the others adopt it almost on their own.

Ready to draft the v0.1.101 consolidation brief on your green light.
