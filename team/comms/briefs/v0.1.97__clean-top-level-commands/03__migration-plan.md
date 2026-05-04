# Migration plan — landing v0.1.97

Mechanical work. Same shape as Phase D D.3 / D.4 (vault / ami regroups in v0.1.96): pure decorator moves, function bodies unchanged.

## Sequence — five small commits

### Commit 1 — Define `sp pw` subgroup and move the 21 top-level commands

In `scripts/provision_ec2.py`:

```python
# right after `app = typer.Typer(...)`
pw_app = typer.Typer(no_args_is_help=True,
                       help='Playwright + agent-mitmproxy stack (the headless API).')
app.add_typer(pw_app, name='playwright')
app.add_typer(pw_app, name='pw',  hidden=True)        # short alias
```

Then for each existing `@app.command(name='X')`, replace with `@pw_app.command(name='X')`. 21 commands.

`scripts/provision_ec2.py:test__app_has_expected_commands` updates: top-level set shrinks; new test `test__pw_subgroup_lists_21_commands` asserts the moved set.

### Commit 2 — Move `sp vault` under `sp pw vault`

The `vault_app` is defined inside `scripts/provision_ec2.py`. Just nest the registration:

```python
# was
app.add_typer(vault_app, name='vault')
app.add_typer(vault_app, name='v',     hidden=True)

# now
pw_app.add_typer(vault_app, name='vault')
pw_app.add_typer(vault_app, name='v',     hidden=True)
```

Tests: `test__vault_subgroup_lists_seven_commands` updates the typer-app path from `app, ['vault', '--help']` to `app, ['pw', 'vault', '--help']`.

### Commit 3 — Move `sp ami` under `sp pw ami`

Same shape as Commit 2. Tests update similarly.

### Commit 4 — Add `sp catalog`

New file `scripts/catalog.py` — typer wrappers over `Stack__Catalog__Service`:

```python
@app.command(name='types')
def cmd_types(): ...                                # GET /catalog/types

@app.command(name='stacks')
def cmd_stacks(type_filter: str = ''): ...          # GET /catalog/stacks?type=...
```

Mounted on the main `sp` app via `add_typer`. Renderers in `cli/catalog/cli/Renderers.py` (mirror the prom/vnc shape).

### Commit 5 — Add `sp doctor`

New file `scripts/doctor.py`. Three subcommands:

```python
@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):                       # `sp doctor` with no args runs all checks
    if ctx.invoked_subcommand is None:
        run_all_checks()

@app.command(name='passrole')
def cmd_passrole(): ...                             # delegates to existing ensure_caller_passrole

@app.command(name='preflight')
def cmd_preflight(): ...                            # account / region / ECR / image presence
```

The existing `sp ensure-passrole` becomes a 1-line call into `cmd_passrole` — or just gets deleted (hard cut per Phase D C1 precedent).

## What doesn't change

- All Tier-1 services (`Linux__Service`, `Docker__Service`, `Vnc__Service`, etc.) — untouched.
- All FastAPI route classes — untouched.
- All schemas, helpers, primitives — untouched.

## What needs touching beyond `scripts/provision_ec2.py`

- `tests/unit/scripts/test_provision_ec2.py` — `test__app_has_expected_commands` shrinks dramatically; the 21 ex-top-level commands move to a new `test__pw_subgroup` test.
- Any operator runbook / brief that uses the old form. Quick grep: `grep -rE 'sp (create|list|delete|connect|shell|env|exec|logs|diagnose|forward|wait|clean|open|screenshot|smoke|health|ensure-passrole|run|vault-|ami |bake-ami|wait-ami|tag-ami|list-amis|create-from-ami)' team/`.
- `team/roles/librarian/reality/v0.1.31/06__sp-cli-duality-refactor.md` — needs a Phase E section and a new "v0.1.97 done" block.
- `team/claude/debriefs/index.md` — one new entry per commit.

## Test discipline

Per CLAUDE.md: every commit ships green and observable. Each of the 5 commits above can land independently — no half-states.

For the typer help-text tests, the existing `_plain(text)` ANSI-stripping helper (used by `tests/unit/sgraph_ai_service_playwright__cli/prometheus/cli/test_typer_app.py` and elsewhere) handles the FORCE_COLOR=1 flake. Copy it into any new test files.

## After v0.1.97

Cleanups that could land later but aren't strictly required:

- Drop `sp ensure-passrole` entirely (now `sp doctor passrole`). Hard cut per the v0.1.96 precedent.
- Add `sp doctor` checks for each section — `sp pw doctor`, `sp vnc doctor`, etc. Each section knows its own preflight (e.g. `sp vnc doctor` checks the chromium image is pullable).
- Add `sp catalog watch [--type X]` for live updates (websocket / polling).
