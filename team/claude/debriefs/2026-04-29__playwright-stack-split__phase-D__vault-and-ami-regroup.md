# Phase D (2/2) — Regroup `vault-*` under `sp vault` + `*-ami` under `sp ami`

**Date:** 2026-04-29.
**Plan:** `team/comms/plans/v0.1.96__playwright-stack-split__07__command-cleanup-and-migration.md`.
**Predecessor:** Phase D (1/2) — drop forward-* / metrics (`d5b5c26`).

---

## What shipped

Per plan doc 7 C1 (hard cut, no transition window) — flat top-level commands regrouped into typer subgroups; flat aliases dropped.

### `sp vault` subgroup (7 commands)

| Was | Now |
|---|---|
| `sp vault-clone <key>` | `sp vault clone <key>` |
| `sp vault-list` | `sp vault list` |
| `sp vault-run <script>` | `sp vault run <script>` |
| `sp vault-commit` | `sp vault commit` |
| `sp vault-push` | `sp vault push` |
| `sp vault-pull` | `sp vault pull` |
| `sp vault-status` | `sp vault status` |

Both `sp vault` and `sp v` (hidden short alias) work.

### `sp ami` subgroup (4 commands)

| Was | Now |
|---|---|
| `sp bake-ami` | `sp ami create` |
| `sp wait-ami` | `sp ami wait` |
| `sp tag-ami` | `sp ami tag` |
| `sp list-amis` | `sp ami list` |

Verbs match the established `sp el ami {create, wait, tag, list}` pattern (per plan doc 7 — convention emerging from sister sections).

`sp create-from-ami` **stays at the top level** — it's a different action (launch an instance from a baked AMI, not an AMI op). This matches the `sp el create-from-ami` precedent.

## How

For each command:

```python
# was
@app.command(name='vault-clone')
def cmd_vault_clone(...): ...

# now
@vault_app.command(name='clone')
def cmd_vault_clone(...): ...
```

The `vault_app` and `ami_app` typer sub-apps are defined just after the main `app` and registered via `add_typer` immediately:

```python
app = typer.Typer(...)

vault_app = typer.Typer(no_args_is_help=True, help='Vault clone/run/commit/push/pull/status/list — ...')
app.add_typer(vault_app, name='vault')
app.add_typer(vault_app, name='v',     hidden=True)   # short alias

ami_app = typer.Typer(no_args_is_help=True, help='AMI lifecycle — bake / wait / tag / list. ...')
app.add_typer(ami_app, name='ami')
```

Decorators at lines 1300-1500 (vault) and 1950-2000 (ami) reference the already-defined sub-apps. Function bodies and signatures unchanged — pure decorator move.

## Tests

| Test | Change |
|---|---|
| `test_cli_surface::test__app_has_expected_commands` | Removed flat `vault-clone` / `vault-list` / ... / `bake-ami` / `wait-ami` / `tag-ami` / `list-amis` from the expected-command set; added `vault` + `ami` subgroup names. |
| **NEW** `test__vault_subgroup_lists_seven_commands` | Asserts `sp vault --help` lists `clone` / `list` / `run` / `commit` / `push` / `pull` / `status`. |
| **NEW** `test__ami_subgroup_lists_four_commands` | Asserts `sp ami --help` lists `create` / `wait` / `tag` / `list`. |

## Test outcome

| Suite | Before | After |
|---|---|---|
| `tests/unit/sgraph_ai_service_playwright__cli/` + `tests/unit/scripts/` | 997 | 999 (+2 new subgroup tests) |

No regressions.

## Files changed

```
M  scripts/provision_ec2.py                       (~+13 / −7 — sub-app definitions + decorator renames)
M  tests/unit/scripts/test_provision_ec2.py       (~+13 / −2 — expected-command set + 2 new subgroup tests)
```

## What `sp --help` looks like now (the goal-state from plan doc 7)

```
Commands:
  create / list / info / delete / connect / shell / env / exec / exec-c / logs /
  diagnose / forward / wait / clean / open / screenshot / smoke / health / run /
  ensure-passrole / create-from-ami / preflight / publish / kibana / metrics
  (and a few more …)

Subcommands:
  vault   (v)         Vault clone/run/commit/push/pull/status/list.
  ami                 AMI bake/wait/tag/list.
  el      (elastic)   Elasticsearch + Kibana stacks.
  os      (opensearch) OpenSearch + Dashboards stacks.
  prom    (prometheus) Prometheus + cAdvisor + node-exporter stacks.
  vnc                 Browser-viewer (chromium + nginx + mitmproxy) stacks.
  linux   (lx)        Bare Linux EC2 stacks.
  docker  (dk)        Docker-on-AL2023 EC2 stacks.
  ob      (observability) AMP/AMG/OpenSearch ephemeral stacks.
```

## Phase D — complete

All four planned regroups done:

1. ✅ Drop `sp forward-prometheus` / `sp forward-browser` / `sp forward-dockge` (Phase D 1/2)
2. ✅ Move `sp metrics` → `sp prom metrics <url>` (Phase D 1/2)
3. ✅ Regroup `sp vault-*` under `sp vault` (this commit)
4. ✅ Regroup `sp *-ami` under `sp ami` (this commit)

## v0.1.96 — done

Phases A → D all shipped. The Playwright stack-split refactor is complete:

- **Phase A** — shared foundations (`Stack__Naming`, `Image__Build__Service`, `Ec2__AWS__Client`)
- **Phase B5** — `sp os` end-to-end (OpenSearch + Dashboards sister section)
- **Phase B6** — `sp prom` end-to-end (Prometheus + cAdvisor + node-exporter)
- **Phase B7** — `sp vnc` end-to-end (chromium + nginx + mitmproxy)
- **Phase C** — strip Playwright EC2 from 9 containers → 2
- **Phase D** — command cleanup (forward-* deleted, metrics moved, vault-* + *-ami regrouped)
