# lets — Proposed

PROPOSED — does not exist yet. Items below extend the LETS CloudFront pipeline but are not in code today.

Last updated: 2026-05-17 | Domain: `lets/`
Sources: "What does NOT exist yet" sections of `_archive/v0.1.31/10,11,12__lets-cf-*.md`.

---

## P-1 · LETS Save layer

**What:** Manifest + screenshot to S3 vault. Slice 1 ships the Load layer (S3 inventory) and slice 2 ships the Extract layer (`.gz` reads + per-event indexing); the Save layer (vault-bucket persistence of run artefacts) is not implemented.

**Source:** Slice 1/2/3 "does not exist yet" sections.

## P-2 · FastAPI duality for `sp el lets`

**What:** Today `sp el lets` is Typer-only. The duality refactor (`Fast_API__SP__CLI`) does not yet expose `/elastic/lets/...` routes.

**Source:** Slice 1/2 "does not exist yet".

## P-3 · Multi-source registry

**What:** One source is hardcoded today — `cf-realtime` for inventory, CloudFront-realtime TSV for events. A registry would let new log sources be added by declaration.

**Source:** Slice 1/2 "does not exist yet".

## P-4 · Stage 3 Transform precompute (rollup indices)

**What:** Today Kibana's own aggregations handle rollups. A precomputed Transform stage would materialise hourly/daily rollups into dedicated indices.

**Source:** Slice 1/2 "does not exist yet".

## P-5 · Stage 1 cleaning module

**What:** The realtime-log config pre-strips `c-ip` / `x-forwarded-for` / cookies, so listing metadata is PII-free. A formal Stage 1 cleaning module would future-proof against config drift.

**Source:** Slice 1 "does not exist yet".

## P-6 · Explicit ES index template

**What:** Today the pipeline relies on auto-mapping. The `.keyword` rule is a known footgun (caught by regression tests). An explicit index template would lock the mappings.

**Source:** Slice 2 "does not exist yet".

## P-7 · `consolidate wipe` / `consolidate list` / `consolidate health`

**What:** Slice 3 ships `consolidate load` only. The full verb set (matched-pair wipe + list + health) is not yet present.

**Source:** Slice 3 module table — only `cmd_consolidate_load` listed under `scripts/elastic_lets.py`.

## P-8 · Other workflow types beyond CONSOLIDATE

**What:** `Enum__Lets__Workflow__Type` declares `CONSOLIDATE / COMPRESS / EXPAND / UNKNOWN`. Only `CONSOLIDATE` has a loader today.

**Source:** Slice 3 enums table.
