# 05 — Acceptance, non-goals, and follow-ups

## Acceptance criteria

The slice is "done" when every box ticks against a freshly-launched
ephemeral Kibana stack:

- [ ] **One command loads today's inventory.** `sp el lets cf inventory load`
  with no flags lists today's S3 prefix, ensures index template + data view
  + dashboard, bulk-posts every record, and prints a summary table that
  includes the Kibana URL.
- [ ] **The dashboard opens and shows 5 populated panels** at the URL the
  load command printed, against today's data, with no manual click-through.
- [ ] **Re-running `load` is idempotent** — the second invocation reports
  `objects_indexed=0, objects_updated={total}` (etag-as-id collapses the
  duplicates).
- [ ] **`wipe` followed by `wipe` is idempotent** — the second invocation
  reports `indices_dropped=0, data_views_dropped=0, saved_objects_dropped=0`.
- [ ] **The wipe-and-reload loop completes cleanly** — `load → wipe -y →
  load` returns the same `objects_indexed` count both times, and the
  dashboard re-appears unchanged.
- [ ] **`--prefix 2026/04` succeeds** (one month of data, ~10–12k docs) on
  the same command surface, no code changes.
- [ ] **`--all` succeeds** on the full bucket — may be slow, but completes
  without OOM.  This pins the "eventually all of it" path.
- [ ] **Tests cover every service path with no mocks** — at least one
  unit test per service-class method, using the in-memory subclasses for
  S3, Elastic HTTP, and Kibana saved-objects.
- [ ] **Reality doc updated.**  A new `team/roles/librarian/reality/v0.1.99/`
  entry (or addition to the current reality folder) declares the new
  CLI commands + module + index + dashboard exist.
- [ ] **Debrief filed.** `team/claude/debriefs/2026-MM-DD__lets-cf-inventory.md`
  with the why / what / how-to-use breakdown if the slice grows beyond a
  single PR; otherwise a single-file debrief is fine.

---

## Non-goals (explicitly out of scope for slice 1)

1. **No `.gz` content reads.**  Not one GetObject call.  All work is from
   `ListObjectsV2` metadata + filename parsing.
2. **No durable Save layer.**  No writes to `lets/raw/`, `lets/extract/`,
   `lets/save/` in S3 or anywhere else.  The S3 bucket is the Load layer
   (AWS-managed, already there); Elastic is the working copy.
3. **No Stage 1 cleaning module.**  The realtime-log config has already
   pre-stripped PII; there's nothing to redact in the listing surface.
   Cleaning gets a real implementation when slice 2 ships content parsing.
4. **No Transform stage.**  Per-hour / per-day rollups are computed by
   Kibana at query time.  An explicit Transform precompute layer is added
   only if query cost becomes a concern.
5. **No FastAPI surface yet.**  Per the existing duality refactor pattern
   (`v0.1.72__sp-cli-fastapi-duality`) the FastAPI mirror of these commands
   is straightforward, but it's a follow-up — slice 1 ships the Typer side
   only.
6. **No screenshot vault commit.**  Slice 1 writes nothing to the vault.
   The Save-layer screenshot work lives in slice 3.
7. **No multi-source generalisation.**  `Enum__LETS__Source__Slug` has one
   value (`CF_REALTIME`).  When the second source arrives we'll reshape;
   for now YAGNI.
8. **No FastAPI route for HTTP-driven scheduling.** Same reason as #5;
   needed for the Lambda-driven daily refresh, but a follow-up.

---

## Follow-up slices (sketched, not committed)

| Slice | Working title | Adds |
|-------|---------------|------|
| **2** | `sp el lets cf events load` | `.gz` content reads → parse TSV → typed event records → second index `sg-cf-events-*` + second dashboard.  Updates inventory docs to `content_processed=true`. |
| **3** | LETS Save layer | `lets/save/{run_id}/manifest.json` + Playwright dashboard screenshot → S3 vault.  Decouples slice-1 / slice-2 dashboards from the live Kibana so they survive `sp el delete --all`. |
| **4** | FastAPI duality | Mirror every `sp el lets cf` command as an HTTP route on `Fast_API__SP__CLI` so the daily morning load can be a scheduled HTTP POST from GitHub Actions or a Lambda. |
| **5** | Second source | Pick: `agent_mitmproxy` audit log, `sgraph-send` app logs, or another CloudFront distribution.  Drives the source registry and shakes out the `cf`-specific assumptions in the slice 1 design. |
| **6** | Stage 1 — real cleaning | When slice 2 brings content fields with `c-ip` / `cs-cookie` / etc., the Stage 1 cleaning module gets actual work to do.  Hash + redact + audit. |
| **7** | Stage 3 — Transform precompute | If Kibana query latency on slice-2 event volume becomes painful, materialise per-minute / per-hour rollup indices. |

---

## Trade-offs surfaced by this design

These are pinned for transparency — the slice ships as designed, but each
trade-off may need revisiting later.

1. **Etag-as-id over per-run indices.** Strong idempotency, slight loss of
   per-run isolation.  Alternative considered: `_id = "{run_id}-{etag}"` for
   full isolation but bloats indices and breaks slice 2's update-by-id
   path.  Decision: etag wins, run-id is informational.
2. **Today-UTC default.** Deterministic but boring (always loads the same
   data twice in a day).  Alternative: "last 24h relative to wall-clock".
   Decision: today-UTC for slice 1 (deterministic re-runs match LETS §16);
   add `--last 24h` later if the use case demands it.
3. **Daily rolling indices.** Easy to drop one day, but multiplies index
   count over time.  Alternative: one `sg-cf-inventory` index forever.
   Decision: daily rolling matches the time partitioning of the source and
   makes "wipe one day" trivial; ILM policy can roll old indices to
   `cold` storage class as a slice-7 concern.
4. **Slice 1 has no FastAPI surface.** Closes off the daily Lambda
   automation path until slice 4.  Acceptable because slice 1 is a
   developer tool — the user types `sp el lets cf inventory load` to
   investigate something, not to keep a dashboard live overnight.

---

## What the architect hands to Dev

This brief.  No code.  Dev's first task on pickup:

1. Read this folder top-to-bottom.
2. Scaffold the module tree from `03__schemas-and-modules.md` (empty
   classes, empty service methods).
3. Write the failing tests against the empty service methods.
4. Implement bottom-up: `S3__Inventory__Lister` first, then
   `Inventory__Loader.load()`, then `Inventory__Wiper.wipe()`, then
   read-side verbs.
5. Land the Typer commands once the service layer green-tests.
6. End-to-end smoke against a real `sp el create-from-ami --wait` stack
   before opening the PR.
