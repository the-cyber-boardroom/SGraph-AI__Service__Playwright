---
title: "`sg vault-app fargate` — timing instrumentation"
status: plan
audience: dinis_cruz
author: claude-opus-4-7
date: 2026-05-19
parent: ./00__overview.md
---

# Timing instrumentation — `Phase__Timer`, live progress, historical store

## Why this gets its own document

Per the brief: "how long actions take will determine what happens next and
how we can expose this to users/customers." The current pattern in `sg vp`
is *ad-hoc* timing — `time.time()` calls sprinkled into command bodies, no
shared utility, no schema field for durations, no historical record.

This document is the proposal to replace that with a single, simple,
schema-typed pattern used across the whole vault-app fargate sub-app — and
that can backport to `sg vp setup` and `sg vp wake` later.

## Survey of what exists today (in the repo)

1. `Cli__Vault_Publish.py:134` — `t_start = time.time()` … `run_ms = int((time.time() - t_start) * 1000)`
2. `Cli__Vault_Publish.py:177–179` — HTTP probe timing inline
3. `Cli__Vault_Publish.py:182` — `total_ms = int((time.time() - t_start) * 1000)`
4. `Cli__Setup.py:673–715` — live-progress renderer for lambda deploy phases
   (state dict, `time.time()` deltas, `rich.live.Live`)
5. `Schema__Vault_App__Create__Response.py:14` — single `elapsed_ms` field
6. **No `Phase__Timer`, `Stopwatch`, or `Timing__Context` utility class
   anywhere** — every call-site rolls its own.
7. **No schema captures per-phase durations** — durations are computed in
   the CLI layer and printed live, never persisted.

We don't want to keep that. The vault-app fargate work is the right place to
introduce a proper utility.

## Proposed: `Phase__Timer` utility

Location: `osbot_utils`-shaped (small, dependency-free, Type_Safe) but
**lives initially under `sg_compute_specs/vault_app/fargate/service/`** so we
ship it without blocking on an osbot release. Move upstream once stable.

```python
# Schema__Phase__Result.py
class Schema__Phase__Result(Type_Safe):
    name        : str                              # 'run-task' etc
    status      : Enum__VAF__Phase__Status         # PENDING / RUNNING / OK / SKIPPED / WARN / ERROR
    duration_ms : int = 0
    started_at  : str = ''                         # ISO-8601 UTC, populated on phase-enter
    error       : str = ''                         # short message, full traceback elsewhere
    detail      : str = ''                         # free-form (e.g. 'state: STOPPED → RUNNING')

# Phase__Timer.py
class Phase__Timer(Type_Safe):
    results      : List__Schema__Phase__Result = None   # accumulated
    progress_cb  : object                       = None   # optional callable(phase_name, status, detail)
    _start_monotonic : float                    = 0.0    # for total_ms()

    def phase(self, name: str) -> '_Phase__CM':
        return _Phase__CM(timer=self, name=name)

    def total_ms(self) -> int:
        return int(sum(r.duration_ms for r in self.results))

    def cumulative_through(self, phase_name: str) -> int:
        # ms from first phase start through end of `phase_name` (inclusive)
        ...

    def json(self) -> dict:
        return {'phases': [r.json() for r in self.results],
                'total_ms': self.total_ms()}

class _Phase__CM:                    # context manager — internal
    def __enter__(self):
        # emit progress(name, RUNNING); record start_monotonic
    def __exit__(self, exc_type, exc, tb):
        # compute duration_ms; if exc_type: status=ERROR, error=str(exc); else status=OK
        # emit progress(name, status, detail)
        # append Schema__Phase__Result to timer.results
        # do NOT swallow exception (return False)
```

### Usage in orchestrators

```python
timer = Phase__Timer(progress_cb=cli_progress_cb)

with timer.phase('run-task'):
    response = fargate_client.run_task(...)

with timer.phase('wait-running'):
    self._poll_until_running(response.task_arn)

with timer.phase('resolve-eni'):
    public_ip = self._resolve_public_ip(response.task_arn)

# At end:
report = Schema__VAF__Start__Report(
    ...,
    phases        = timer.results,
    task_ready_ms = timer.cumulative_through('wait-running'),
    vault_ready_ms = timer.cumulative_through('wait-http-health'),
    total_ms      = timer.total_ms(),
)
```

### Why a context manager (and not decorators or hooks)

- Visible at the call-site — readers see exactly which lines are being timed
- Exception-safe — `__exit__` always runs, always records duration, always
  emits the progress callback so the live table renders failure states
- Pickle-free — no decorator magic, no `inspect`, no class registry

## Live progress renderer (re-usable)

Extract from `Cli__Setup.py:673–715` into a re-usable class:

```python
# Phase__Progress__Renderer.py
class Phase__Progress__Renderer(Type_Safe):
    console : object = None                           # rich.console.Console
    title   : str    = 'Phases'
    phases  : list   = None                           # ordered list of (name, description)

    def __enter__(self):
        # initialise state dict {name: {status, started_at, elapsed}}
        # spin up rich.live.Live with refresh_per_second=4
        return self

    def __exit__(self, *exc):
        # finalise table (final render with totals row)
        # close Live context

    def on_phase(self, name: str, status: str, detail: str = ''):
        # update state, re-render table; called by Phase__Timer.progress_cb

    def _build_table(self) -> rich.table.Table:
        # Status / Phase / Elapsed / Detail
        # icons via Enum__VAF__Phase__Status (see below)
```

### Status icons

```python
_STATUS_ICON = {
    Enum__VAF__Phase__Status.PENDING : '[dim]⏳ pending[/]',
    Enum__VAF__Phase__Status.RUNNING : '[cyan]▶ running[/]',
    Enum__VAF__Phase__Status.OK      : '[green]✓ ok[/]',
    Enum__VAF__Phase__Status.SKIPPED : '[yellow]≡ skip[/]',
    Enum__VAF__Phase__Status.WARN    : '[yellow]⚠ warn[/]',
    Enum__VAF__Phase__Status.ERROR   : '[red]✗ error[/]',
}
```

Matches `_STATE_ICON` in `Cli__Setup.py:923–929` — same visual language.

### Final render (after Live exits)

```
╭─ Setup phases ────────────────────────────────────────────╮
│ Status       Phase          Elapsed   Detail              │
│ ✓ ok        ecr             1.2s      repo exists         │
│ ✓ ok        iam             3.4s      role created        │
│ ✓ skip      logs            0.0s      group already exists│
│ ✓ ok        cluster         0.9s      cluster up          │
│ ✓ ok        task-def        2.1s      revision :7         │
│ ─────────────────────────────────────────────────────────  │
│ Total                       7.6s                          │
╰───────────────────────────────────────────────────────────╯
```

## JSON envelope (downstream contract)

Every command that runs phases includes this in its `--json` output:

```json
{
  "phases": [
    {"name": "ecr",     "status": "ok",   "duration_ms": 1200, "detail": "repo exists"},
    {"name": "iam",     "status": "ok",   "duration_ms": 3400, "detail": "role created"},
    {"name": "logs",    "status": "skip", "duration_ms":   12, "detail": "group already exists"},
    {"name": "cluster", "status": "ok",   "duration_ms":  900, "detail": "cluster up"},
    {"name": "task-def","status": "ok",   "duration_ms": 2100, "detail": "revision :7"}
  ],
  "total_ms": 7612
}
```

Stable field names. Consumed by:
- The `timings` CLI command
- Eventual customer-facing API (when we expose "give me a vault" as a
  service) — these numbers go on the SLO dashboard
- The historical timings store (next section)

## Historical timings store

`Vault_App__Fargate__Timings__Store` (described in
[03](./03__orchestrator-design.md)) writes each `Schema__VAF__Start__Report`
to `~/.cache/sg/vault-app-fargate/timings.json` as an append-only JSONL.

`sg vault-app fargate timings --last 10` reads + renders:

```
╭─ Last 10 starts (slug: dinis-tue) ────────────────────────╮
│ When                  task_ready  vault_ready  total      │
│ 2026-05-19 00:14:33    4.1s        9.7s         13.8s     │
│ 2026-05-19 00:01:22    4.0s        9.2s         13.2s     │
│ 2026-05-18 23:48:14    4.3s       10.1s         14.4s     │
│ ...                                                       │
│ p50                    4.1s        9.7s         13.5s     │
│ p95                    4.5s       12.1s         16.0s     │
╰───────────────────────────────────────────────────────────╯
```

This is what tells you "the cluster's image-pull is slow today" or "DNS
propagation is dragging things" before you wonder why your demo's slow.

## Optional: CloudWatch metric publication

P2 — gated behind a `--publish-metrics` flag (or repo config). Publishes:

- `VaultApp/Fargate/Start/TaskReadyMs` (gauge)
- `VaultApp/Fargate/Start/VaultReadyMs` (gauge)
- `VaultApp/Fargate/Start/TotalMs` (gauge)
- `VaultApp/Fargate/Start/<phase>` (per-phase, e.g. `RunTaskMs`, `WaitRunningMs`)

Dimensions: `Slug`, `Region`, `LaunchType` (`FARGATE` vs `FARGATE_SPOT`).

Useful once we're running this for customers — you can spot regressions
across the fleet. Skip in v1. The `Schema__VAF__Start__Report` envelope is
already shaped right for it.

## What we are NOT doing here

- **Not building a tracing library.** No spans-with-parent-ids,
  no OpenTelemetry adapter. Just phases. If a phase has internal sub-stages
  worth measuring, it gets its own nested `Phase__Timer` and reports a
  flattened list (no tree).
- **Not measuring per-AWS-call latency.** That's `boto3`'s job (it ships with
  an event system if you ever want it). Phase-level granularity is the right
  altitude for a CLI-facing UX.
- **Not measuring inside the container.** Vault boot time is one phase from
  outside (`WAIT_HEALTH`). If the container team wants finer-grained internal
  startup numbers they'll publish them in `/info/health` or similar; we'll
  forward them in `Schema__VAF__Start__Report.detail` if present.

## Migration path for `sg vp`

Once `Phase__Timer` ships and proves out in vault-app fargate, refactor
`sg vp wake` (`Cli__Vault_Publish.py:95–196`) and `Cli__Setup._run_with_lambda_progress`
(`Cli__Setup.py:673–715`) to use it. Both currently roll their own.

Not part of this plan — separate slice once the utility is battle-tested.

## Reading order

Continue to [`05__implementation-slices.md`](./05__implementation-slices.md)
for the shippable ordering.
