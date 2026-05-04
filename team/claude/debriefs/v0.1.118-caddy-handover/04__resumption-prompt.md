# 04 — Resumption prompt

Copy the block below into a fresh Claude Code session (Sonnet works well —
this is the kind of incremental work it's tuned for). The agent will pick
up the project state, read the rules and history, and ask you what to
work on first.

---

```
You are continuing work on the SG Playwright Service repo. The session
that came before you wrapped up the v0.1.118 caddy-swap slice (commit
b9123d1 on branch claude/refactor-playwright-stack-split-Zo3Ju).

Before writing any code, read these in order:

  1. .claude/CLAUDE.md                           ← project rules (non-negotiable)
  2. library/catalogue/README.md                  ← fractal index
  3. team/roles/librarian/reality/README.md       ← points at current truth doc
  4. team/claude/debriefs/v0.1.118-caddy-handover/00__README.md
     and the 4 sibling files in that folder
  5. team/roles/dev/ROLE.md                       ← role you're stepping into

Then check open threads in
team/claude/debriefs/v0.1.118-caddy-handover/02__open-threads.md and ask
me which one to start with. Do NOT pick one yourself — wait for me to say.

Branch discipline:
  - Default branch is `dev`. Never push to dev directly.
  - Continue on `claude/refactor-playwright-stack-split-Zo3Ju` unless I
    explicitly ask for a new branch.
  - After every meaningful change: run the unit suite, sync from
    origin/dev, commit with a clear message, push.

Patterns to follow (these are caught in review):
  - Every class extends Type_Safe (osbot-utils). No plain Python classes.
  - No Pydantic, no Literal, no unittest.mock / @patch / monkeypatch.
    Tests use _Fake_* subclasses that override the I/O seam.
  - One class per file. __init__.py files stay empty.
  - Routes have no logic — pure delegation to <Section>__Service.
  - Schemas are pure data, no methods. Collection classes likewise.
  - 80-char ═══ headers on every file.
  - Inline comments only — no docstrings ever.
  - Pin all Docker image tags (we got bitten by `:latest` in this session
    on mitmproxy and caddy).

When you spot a problem the previous session already solved, check
team/claude/debriefs/v0.1.118-caddy-handover/01__where-we-are.md ("Recent
debug history") before re-debugging it.

Verify your environment:
  pytest binary: /tmp/venv-sp/bin/pytest
  Run: pytest tests/unit/ --ignore=tests/unit/agent_mitmproxy/test_Routes__CA.py -q
  Expected: 1998 passed, 1 skipped (or higher if dev moved).

Now confirm you've read the handover and ask what to work on.
```

---

## Why this prompt is shaped this way

- **Forces reading order** — the project relies on the reality doc + briefs
  to ground the agent. Skipping these leads to inventing facts.
- **Explicit "ask first, don't pick"** — the open-threads file lists 7
  threads ranked by urgency, but the human is the one with context on
  business priority. Sonnet sometimes runs ahead and picks the most
  technically interesting one.
- **Branch + push discipline** — multiple agents have been working on
  this branch in parallel (it's why every session merges from origin/dev
  before committing). Forgetting this causes merge conflicts.
- **Pattern reminders inline** — these are also in CLAUDE.md, but
  repeating the top-3 (Type_Safe, no mocks, pin images) saves a review
  round-trip.
- **Verification command** — running the suite once on entry confirms
  the venv is wired up and the agent inherits a green baseline. If it
  fails, we know it's environment, not the code we're about to write.

## What the new agent should NOT do on entry

- Edit code before reading the docs above.
- Write a debrief / plan file before agreeing what to work on.
- Push directly to `dev`.
- Touch files under `team/humans/dinis_cruz/briefs/` or
  `team/humans/dinis_cruz/debriefs/` — those are HUMAN-ONLY.
