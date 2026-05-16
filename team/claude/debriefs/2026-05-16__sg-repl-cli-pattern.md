---
title: "sg repl — interactive REPL shell for any Typer CLI"
date: 2026-05-16
status: COMPLETE
branch: claude/fix-sg-compute-cli-nZaW6
merged: false
area: sg-compute / cli
---

# sg repl — Interactive REPL Shell Pattern

## Header

| Field | Value |
|-------|-------|
| **Date** | 2026-05-16 |
| **Status** | COMPLETE |
| **Versions shipped** | none — no version bump (pure CLI UX work) |
| **Branch** | `claude/fix-sg-compute-cli-nZaW6` — **not yet merged to `dev`** |

### Commits this session

| Hash | Message |
|------|---------|
| `51eeb4d` | fix(sg-cli): sort commands alphabetically, shorten help text, add sg nodes |
| `ae58264` | feat(sg-repl): add `sg repl` interactive shell |
| `c5c475b` | feat(sg-repl): add help and h as aliases for ? |
| `10cdc62` | fix(sg-repl): help/h/? now delegate to real sg --help output |
| `bb6a724` | refactor(sg-repl): generic dispatch — no hardcoded section registry |
| `7c636f6` | feat(sg-repl): prefix matching for sections and verbs |
| `22b621b` | feat(sg-repl): arbitrary-depth navigation via path list |
| `90ccde2` | feat(sg-repl): multi-word execute vs single-word navigate |

---

## TL;DR for the next agent

1. **`sg repl` is a ~80-line wrapper** over the existing `sg` Typer app — it adds zero parallel command logic. Everything dispatches via `sg_app(path + args)`. Do not add hardcoded command tables.
2. **The pattern is fully generic** — `run_repl(sg_app)` takes any Typer app and works. Apply it to any other CLI by passing a different app reference.
3. **Branch is unmerged** — merge `claude/fix-sg-compute-cli-nZaW6` to `dev` before the next session.
4. **No new tests written** — the REPL has no unit tests yet; the existing CLI tests still cover the underlying commands. A follow-up should add REPL navigation tests using `typer.testing.CliRunner`.
5. **Reality doc not updated** — the sg-compute domain reality doc does not yet mention `Cli__SG__Repl.py` or the `sg repl` command. Update `team/roles/librarian/reality/sg-compute/index.md` on merge.

---

## Why we built this

The `sg` CLI grew to 17+ sub-commands (playwright, elastic, docker, nodes, ollama, aws, …). Each sub-command has 4–8 verbs. Navigating it looks like:

```
sg nodes list
sg aws billing week
sg playwright create --region eu-west-2
```

For interactive exploration this is slow. The user also wanted a shorter way to:
- See all live instances (`sg nodes list`)
- Delete stacks (`sg nodes delete-all`)
- Navigate into an area and run several commands without re-typing the prefix

The REPL solves this without any new concept — it's a thin shell that wraps what already exists.

---

## How it works

### Core idea: delegate everything back to the Typer app

The key insight: don't build a parallel registry of commands and functions. Instead, introspect the live Click command tree (which Typer builds automatically) and pass every user input back through `sg_app(args)`.

```python
def _invoke(sg_app, args):
    try:
        sg_app(args, standalone_mode=True)
    except SystemExit:
        pass
```

That single function is all the dispatch the REPL needs. It catches `SystemExit` because Typer/Click raises it after every command (including `--help`).

### Discovering the command tree

```python
def _click_node(sg_app, path):
    node = typer.main.get_command(sg_app)      # Typer → Click conversion
    for segment in path:
        node = node.commands.get(segment)
    return node

def _children(sg_app, path):
    node = _click_node(sg_app, path)
    return {name for name, cmd in node.commands.items() if not cmd.hidden}

def _is_group(sg_app, path):
    node = _click_node(sg_app, path)
    return bool(node and hasattr(node, 'commands') and node.commands)
```

`typer.main.get_command(app)` converts a Typer app to its underlying Click group. From there, `.commands` is a plain dict keyed by command name. Hidden commands are excluded from navigation. This is zero-maintenance — add a new `add_typer()` call to `Cli__SG.py` and the REPL picks it up immediately on next `sg repl`.

### Prefix matching

```python
def _match(prefix, options):
    return sorted(o for o in options if o.startswith(prefix))
```

`p` → `['playwright', 'podman', 'prometheus']` (show candidates)
`pl` → `['playwright']` (sole match — act on it)

Used at every level: root sections and per-section verbs.

### Multi-word resolution: `_resolve()`

The most important function. Walks the click tree across multiple words, resolving each as a prefix:

```python
def _resolve(sg_app, base_path, words):
    current = list(base_path)
    for i, word in enumerate(words):
        if word.startswith('-') or not _is_group(sg_app, current):
            return current, list(words[i:])          # rest are args
        hits = _match(word, _children(sg_app, current))
        if len(hits) == 1:
            current.append(hits[0])
        elif len(hits) > 1:
            return None, hits                         # ambiguous
        else:
            return current, list(words[i:])           # no match → rest are args
    return current, []
```

Stops resolving when it hits an option flag (`-`), a leaf command, or no child matches — everything from that point becomes trailing args.

### The navigate vs execute decision

The loop calls `_resolve()` on every input, then applies one rule:

```
ambiguous            →  show candidates
single word → group  →  navigate (push to path, show help)
everything else      →  execute without navigating
```

```python
resolved, trailing = _resolve(sg_app, path, parts)

if resolved is None:
    console.print(f'  [dim]{" ".join(trailing)}[/dim]')
elif len(parts) == 1 and not trailing and _is_group(sg_app, resolved) and resolved != path:
    path[:] = resolved
    _invoke(sg_app, path + ['--help'])
else:
    _invoke(sg_app, resolved + trailing)
```

The `path` list is the entire navigation state. Prompt is derived from it: `'sg/' + '/'.join(path) + '> '`.

---

## Examples in action

### Basic navigation

```
$ sg repl

  SG/Compute shell  —  type a section to enter it, help to list all

sg> help
  (renders the full `sg --help` panel — exactly what `sg` shows)

sg> nodes
  (renders `sg nodes --help`)

sg/nodes> list
  node-id        spec-id   state    instance-type   public-ip   region
  quiet-fermi    docker    running  t3.medium        1.2.3.4    eu-west-2

sg/nodes> delete quiet-fermi
  Delete 'quiet-fermi' in eu-west-2? [y/N] y
  Deleted: quiet-fermi

sg/nodes> ..
sg> q
```

### Prefix matching at root

```
sg> p
  playwright  podman  prometheus

sg> pl
  (enters playwright — sole match)

sg/playwright> l
  (dispatches sg playwright list)
```

### Arbitrary depth

```
sg> aws
sg/aws> bil
sg/aws/billing> w
  (dispatches sg aws billing week — shows spend chart)

sg/aws/billing> ..
sg/aws> ..
sg>
```

### Multi-word: run without navigating

```
sg/aws> billing chart
  (dispatches sg aws billing chart — stays at sg/aws>)

sg/aws> b c
  (prefix-resolves to sg aws billing chart — same result)

sg/aws> b week --days 3
  (dispatches sg aws billing week --days 3)
```

---

## Failure classification

**Good failure — hardcoded `SECTIONS` dict (commit `bb6a724`).**
The first version of the REPL had a `SECTIONS = {'nodes': {...}}` dict mapping section names to function references. After 150 lines the user pointed out that `playwright` didn't work. Root cause: every section not in the dict raised "Unknown section." The fix — discover sections from the live Click tree — reduced the file from 180 to 65 lines and made every future section automatically available. This is a textbook good failure: caught immediately by trying the feature, fixed with a better design.

**Good failure — `help`/`?` showed a custom mini-list instead of the real CLI output.**
The initial `_print_root()` printed a custom-formatted list of sections. The user correctly pointed out "I should literally see what `sg` shows." Replacing with `sg_app(['--help'])` eliminated a parallel description that would have drifted. Again: caught immediately, fixed cleanly.

---

## Lessons learned

### Typer internals

- `typer.main.get_command(app)` converts a Typer app to its Click representation. Available without importing Click directly.
- `click_group.commands` is a plain `dict[str, Command]`. Sub-groups (`add_typer` calls) have a `.commands` attribute; leaf commands do not. `hasattr(node, 'commands')` is the reliable check.
- `app(args, standalone_mode=True)` + catch `SystemExit` is the right way to invoke a Typer app programmatically. `standalone_mode=False` returns values instead of printing, which is wrong for a passthrough REPL.
- Hidden commands (`hidden=True` in `add_typer()`) are excluded from `.commands` iteration when you filter `cmd.hidden`. Always filter them — the aliases (`pk`, `el`, `ff`, etc.) pollute the prefix-match candidates badly if included.

### REPL design

- **Pass the app in, don't import it.** `run_repl(sg_app)` avoids circular imports (Cli__SG.py imports Cli__SG__Repl; if the repl imported Cli__SG back, Python's import system would deadlock).
- **`readline` is all you need for basic UX.** `import readline` (stdlib, no install) gives arrow-key history for free on Linux/Mac. No `prompt_toolkit` needed for this level of interactivity.
- **The prompt is the state.** Derive `prompt = 'sg/' + '/'.join(path) + '> '` from the path list. Users always know where they are.
- **0 matches → pass through verbatim.** Let Typer print its own "No such command" error. Do not duplicate error handling.

---

## Reusing this pattern in another CLI

The entire pattern is three steps:

**1. Copy `Cli__SG__Repl.py` verbatim** (or import `run_repl` from it).

**2. Add a `repl` command to any Typer app:**

```python
# In your_cli.py
@app.command()
def repl():
    """Interactive shell."""
    from your_package.cli.Repl import run_repl
    run_repl(app)
```

**3. That's it.** The REPL discovers sections, verbs, help text, hidden status — all from the live Click tree. No additional configuration.

The only things to customise:
- `DEFAULT_REGION` if your CLI has an AWS region concept
- The exclusion set `- ({'repl'} if not current else set())` — exclude any commands that shouldn't be navigable (e.g. the repl itself, `version`, `doctor`)

---

## Files changed this session

### New files

| File | Purpose |
|------|---------|
| `sg_compute/cli/Cli__SG__Repl.py` | The REPL — 80 lines, fully generic |

### Modified files

| File | Change |
|------|--------|
| `sg_compute/cli/Cli__SG.py` | Commands sorted alphabetically; short `help=` on every `add_typer()`; `sg nodes` sub-group added; `repl` command wired |
| `sg_compute/cli/Cli__Compute__Node.py` | `delete-all` command added |

### Tests

No new tests this session. Existing CLI tests unaffected.

---

## Test status

| Suite | Status |
|-------|--------|
| `sg_compute__tests/` (excluding tls/, control_plane/) | 394 passed, 14 failed, 34 skipped |
| 14 failing | Pre-existing on `dev` — `_FakeLaunch.run_instance()` missing `instance_profile_name` kwarg in Ollama tests; Section__Shutdown systemd timer test; Firefox stub tests |
| tls/, control_plane/ | Fail at collection — `cryptography` C-extension incompatible with this env's Python. Pre-existing environment gap, not introduced this session. |

---

## Open questions

1. **REPL unit tests** — worth adding `typer.testing.CliRunner`-based tests for REPL navigation? Recommended: yes, one test per navigate/execute/prefix/ambiguous case.
2. **`delete-all` in `Cli__Compute__Node`** — should confirmation default to `--yes` when called non-interactively from scripts? Currently always prompts unless `--yes` is passed.

---

## Follow-ups

### Must-do before merging

- [ ] Merge `claude/fix-sg-compute-cli-nZaW6` to `dev`
- [ ] Update `team/roles/librarian/reality/sg-compute/index.md` — add `Cli__SG__Repl.py` and the `sg repl` command to the EXISTS section

### Next slice (if wanted)

- Wire the REPL pattern into `sgraph_ai_service_playwright__cli/aws/cli/Cli__Aws.py` as `sg aws repl` for the DNS/billing/ACM surface
- Add REPL navigation unit tests

### Smaller / opportunistic

- The 14 pre-existing test failures (`_FakeLaunch` kwarg mismatch, Section__Shutdown systemd timer) are worth fixing in a dedicated short slice — they are real bugs in the test doubles, not in the CLI.

---

## Where to start (continuing this work)

1. Read `sg_compute/cli/Cli__SG__Repl.py` — the whole pattern is there, 80 lines.
2. Read `sg_compute/cli/Cli__SG.py` — understand how sections are registered (each `add_typer()` call with a `name=` and `help=`).
3. Read `sg_compute/cli/Cli__Compute__Node.py` — to understand the `delete-all` addition and the `_platform()` seam.
4. Do NOT touch `Cli__SG__Repl.py` to add hardcoded section logic — the whole point is that it stays generic.

Critical invariant: **`run_repl(sg_app)` must receive the app object, not import it** — circular import risk if the module is imported at module level inside the repl file.
