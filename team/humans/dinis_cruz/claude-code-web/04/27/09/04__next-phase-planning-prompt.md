# 04 — Next Phase Planning Prompt

**Your task:** Design the next phases of the `sp el lets cf sg-send` command
suite and the LETS workflow more broadly.  Produce a phased implementation
plan that the Dev role can pick up.

---

## Context recap (one paragraph)

Two LETS pipeline slices exist and are proven in production.  Slice 1
(`sp el lets cf inventory`) lists S3 metadata into Kibana.  Slice 2
(`sp el lets cf events`) reads `.gz` content, parses 38-field CloudFront
event records, and links back to slice 1 via `content_processed`.  A
convenience layer (`sp el lets cf sg-send`) has two diagnostic commands
(`files` and `view`).  One infrastructure class — `Call__Counter` — was
written with a forward declaration: its docstring names
`SG_Send__Orchestrator` as the class that will wire a single counter across
all collaborators.  That class does not exist yet.

---

## The missing piece — `SG_Send__Orchestrator`

The `Call__Counter` docstring is unambiguous:

> *"SG_Send__Orchestrator — constructs ONE counter, injects into every
> collaborator so the final tallies span the whole run."*

This class is the **daily-refresh coordinator** for the SGraph-Send bucket.
It should replace the current two-step manual recipe:

```bash
# Current (manual, two commands)
sp el lets cf inventory load
sp el lets cf events load --from-inventory --max-files 100
```

With a single command:

```bash
# Proposed
sp el lets cf sg-send sync [--date MM/DD] [--max-files N] [--dry-run]
```

### What `SG_Send__Orchestrator` must do

1. Accept a date (default: today UTC) and resolve it to an S3 prefix
2. Run `Inventory__Loader.load()` for that date  
   — injects the shared `Call__Counter`
3. Run `Events__Loader.load(from_inventory=True, ...)` for the same run  
   — injects the same `Call__Counter`
4. Aggregate both responses into a single `Schema__SG_Send__Sync__Response`
5. Surface step-by-step progress via an injected `Progress__Reporter`
6. Return: files listed, files fetched, events indexed, manifest flips,
   S3 calls total, Elastic calls total, wall time

### Design constraints

- Pure logic — no boto3, no requests, no Typer in the orchestrator itself
- Injected collaborators (follows the same pattern as `Inventory__Loader`
  and `Events__Loader`)
- Idempotent — re-running a `sync` for the same date is safe
- The shared `Call__Counter` is the new thing here; everything else is
  composition of existing classes

---

## Planned commands to design

### Tier 1 — Core orchestration (highest priority)

**`sp el lets cf sg-send sync [--date MM/DD] [--max-files N] [--dry-run]`**

Daily refresh for one date.  Runs inventory load → events load
`--from-inventory` in sequence, sharing a `Call__Counter`.  Output: one
unified summary table (inventory stats + events stats + call counts +
wall time).

**`sp el lets cf sg-send status [--date MM/DD]`**

Read-only health check across both slices for a given date (default:
today).  No S3 calls — only Elastic queries.

Example output:

```
  sg-send status · 2026-04-27

  inventory    425 files · 425 indexed · 418 processed · 7 pending
  events       418 files · 4,312 events · 2026-04-27 12:00 → 23:59
  health       inventory ✓  events ✓  manifest-link 98.3% complete

  suggested:   sp el lets cf sg-send sync --date 04/27 --max-files 10
```

---

### Tier 2 — Backfill (medium priority)

**`sp el lets cf sg-send backfill [--from MM/DD] [--to MM/DD] [--max-files-per-day N] [--dry-run]`**

Walk a date range and run `sync` for each date in order.  Should be safe to
interrupt (each per-date sync is already idempotent).

Questions to answer in the plan:
- Does it call `sync` for each date, or does it call `inventory load` for
  the entire range first, then `events load --from-inventory`?
- What's the right `--max-files-per-day` default to keep each iteration
  fast (suggest ~50)?
- How should it report progress — one line per date, or one line per file?

---

### Tier 3 — Nice to have

**`sp el lets cf sg-send report [--date MM/DD]`**

Human-readable daily traffic summary printed to stdout.  Reads from
`sg-cf-events-*` only (no S3).  Suggested sections:
- Top 10 URIs by hit count
- Status class breakdown (2xx / 3xx / 4xx / 5xx)
- Bot vs. human ratio
- Top countries
- Busiest hour

This is a pure-read command — no writes, no S3, no manifest updates.

**`sp el lets cf sg-send wipe-all [-y]`**

Calls `inventory wipe` then `events wipe` in one command.  Convenience only
— both already exist individually.

---

## New schemas to design

The planning session should specify:

| Schema | Fields | Notes |
|--------|--------|-------|
| `Schema__SG_Send__Sync__Request` | `date`, `max_files`, `dry_run`, `bucket`, `region` | Input to the orchestrator |
| `Schema__SG_Send__Sync__Response` | `inventory_load` (embed `Schema__Inventory__Load__Response`), `events_load` (embed `Schema__Events__Load__Response`), `s3_calls_total`, `elastic_calls_total`, `wall_ms`, `sync_date` | Unified result |
| `Schema__SG_Send__Status__Response` | Per-slice counts + health checks + suggested next command | Output of `status` |

---

## Module layout to propose

Current sg-send tree only has services.  The planning session should decide
whether to add:

```
elastic/lets/cf/sg_send/
  schemas/
    Schema__SG_Send__Sync__Request.py
    Schema__SG_Send__Sync__Response.py
    Schema__SG_Send__Status__Response.py
  service/
    SG_Send__Orchestrator.py          (the missing class)
    SG_Send__Status__Reader.py        (read-only, for the status command)
    SG_Send__Date__Parser.py          (already exists)
    SG_Send__File__Viewer.py          (already exists)
    SG_Send__Inventory__Query.py      (already exists)
```

---

## Questions the plan must answer

1. **Orchestrator injection pattern** — `SG_Send__Orchestrator` must accept
   an `Inventory__Loader` and an `Events__Loader` (both fully wired).
   How does it wire the shared `Call__Counter`?  Does it replace the
   counters on the injected loaders, or does it accept pre-wired loaders
   from a factory function?

2. **`sync` vs. `load + load` atomicity** — if `inventory load` succeeds
   but `events load` fails partway through, what's the state?  The plan
   should describe the failure mode and whether it's acceptable for v1.

3. **`--skip-processed` vs. `--from-inventory`** — slice 2's events load
   has two dedup strategies.  The orchestrator should pick one (or expose
   both).  The plan should recommend which is the right default for `sync`.

4. **Tier 2 backfill architecture** — per-date `sync` calls vs. bulk
   inventory load then bulk events load.  Trade-offs: per-date is simpler
   and interruptible; bulk inventory first is fewer S3 list calls.

5. **Reality doc update** — the reality doc is stale (stuck at v0.1.31
   contents, written 2026-04-20).  The LETS commands are a significant
   surface that isn't documented there.  The plan should include a librarian
   task to update `team/roles/librarian/reality/` to reflect the current
   state.  Suggest it becomes a `v0.1.99/` folder with one file for the
   lets slice.

---

## Output format expected

A set of implementation phase documents following the same pattern as the
existing briefs:

```
team/comms/briefs/v0.1.XXX__sp-el-lets-sg-send-orchestrator/
  README.md          Status, decisions, file index
  01__principle.md   Why + what the orchestrator does
  02__cli-surface.md Commands, flags, output examples
  03__schemas.md     New schemas + module layout
  04__phases.md      PR-sized implementation phases for Dev
```

Version number: `v0.1.99` is taken (inventory slice 1 brief).
`v0.1.100` is taken (events slice 2 brief).  Use `v0.1.101` or confirm
the current version from `sgraph_ai_service_playwright/version`.

---

## Existing patterns to follow

Before writing any phase plan, make sure to look at how the existing briefs
are structured:

- `team/comms/briefs/v0.1.99__sp-el-lets-cf-inventory/06__implementation-phases.md`
  — the phase breakdown for slice 1.  Each phase ends with a demo / green
  tests.  No half-finished phases on `dev`.

- `team/comms/briefs/v0.1.100__sp-el-lets-cf-events/06__implementation-phases.md`
  — phase breakdown for slice 2.  Note the "side-effect analysis" table at
  the top (which existing files are modified, which are new).

The same structure should be used for the orchestrator slice.

---

## Things NOT to redesign

- The existing `inventory` and `events` commands — they are stable.
- The `sg-send files` and `sg-send view` commands — they are stable.
- The `Call__Counter` and `Step__Timings` classes — they are ready to use.
- The `Progress__Reporter` base class — extend it, don't change it.
- The `Inventory__HTTP__Client` — it's shared and stable.

---

## One final note on scope

The `sg-send` layer is intentionally a **convenience wrapper** with
hardcoded sgraph-send specifics (bucket name, year defaulting to 2026, etc).
The underlying `inventory` and `events` commands remain generic and
bucket-agnostic.  The orchestrator should follow the same pattern: all
sgraph-send specifics live in `SG_Send__*` classes; the generic slice 1/2
classes are reused as-is.
