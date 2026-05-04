# Backend session kickoff — paste this into a fresh Claude Code session

You are the **v0.2.x backend Sonnet team** for SG/Compute. Read this in full before doing anything.

---

## Your identity

- **Repo:** `the-cyber-boardroom/SGraph-AI__Service__Playwright` @ `v0.2.0` (just merged to main)
- **Branch base:** `dev`
- **Eventual target repo:** `sgraph-ai/SG-Compute`
- **Counterpart:** a parallel **frontend** Sonnet team running in another session — coordinate via the briefs, not directly

## Your first 30 minutes — read in this order

1. `.claude/CLAUDE.md` — project rules (Type_Safe, no Pydantic, no mocks, etc.)
2. `team/comms/briefs/v0.2.0__sg-compute__architecture/00__README.md` — vision + ratified decisions
3. `team/comms/briefs/v0.2.0__sg-compute__architecture/01__architecture.md` — taxonomy, two-package split, spec contract
4. `team/comms/briefs/v0.2.0__sg-compute__architecture/02__node-anatomy.md` — why `linux` was dropped; AMI + Docker + sidecar baseline
5. `team/comms/briefs/v0.2.0__sg-compute__architecture/03__sidecar-contract.md` — first-class sidecar architecture
6. `team/comms/briefs/v0.2.0__sg-compute__architecture/sources/code-review-synthesis.md` — distilled findings from the 6 audit/review reports (good context for *why* the gaps need closing)
7. **Your folder:** `team/comms/briefs/v0.2.0__sg-compute__backend/00__README.md` — phase index + cross-cutting rules

## Recommended execution order

```
BV2.1 → BV2.4 → BV2.3 → BV2.5 → BV2.2 → BV2.6 → BV2.7 → BV2.8 → BV2.9 →
BV2.10 → BV2.11 → BV2.12 → BV2.13 → BV2.14 → BV2.15 → BV2.16 → BV2.17 → BV2.18
```

Why: BV2.1 is lowest-risk; BV2.4 sets the "no logic in routes" pattern; BV2.3 + BV2.5 unblock frontend; BV2.7 is the disruptive migration (wait until earlier phases stabilise); BV2.8-BV2.12 dismantle dual-write in dependency order; BV2.13-BV2.14 raise quality before PyPI; BV2.15 waits on Architect locks; BV2.17 waits on frontend FV2.8.

## Your first phase: **BV2.1 — Delete orphan `sgraph_ai_service_playwright__host/`**

File: [`BV2_1__delete-orphan-host.md`](BV2_1__delete-orphan-host.md). Smallest possible PR. Verify nothing imports the orphan; `git rm -r`; CI green; reality doc updated.

**Stop after BV2.1.** Wait for the human to ratify and tell you which phase to do next. Do NOT auto-pick BV2.4.

## Hard rules (binding every session)

- **Type_Safe everywhere.** No Pydantic. No raw `str/int/list/dict` attributes. No Literals. **No `: object = None` for DI.**
- **One class per file.** Empty `__init__.py`. Schemas, primitives, enums, collection subclasses each in their own file.
- **Routes have no logic** — pure delegation to a service class.
- **`osbot-aws` for AWS** — no direct boto3.
- **Tests: no mocks, no patches.** `unittest.mock.patch` is forbidden in `sg_compute__tests/`.
- **80-char `═══` headers** on every Python file.
- **No docstrings** — single-line inline comments only where the WHY is non-obvious.
- **Branch:** `claude/bv2-{N}-{description}-{session-id}`. Never push to `dev` directly.
- **PR title:** `phase-BV2.{N}: {short summary}`.
- **PR description:** link to the phase file; list the acceptance criteria you checked.
- **Update reality doc** in same commit; append pointer entry to `team/roles/librarian/reality/changelog.md`.
- **One phase per PR. One PR per session.** No big-bang refactors.
- **CLAUDE.md rule 9** (no underscore-prefix for private methods) applies **Python only**.

## Coordination signals you may receive

- **Architect locks needed** before specific phases — phase files flag these. Don't start BV2.15 until cookie + CORS decisions are locked. Don't start BV2.7 until `__cli/aws/` destination is ratified.
- **Frontend phases that depend on yours:**
  - FV2.7 (Pods tab unified URL) needs **BV2.3** to ship.
  - FV2.5 (launch flow 3 modes) needs **BV2.5** to ship.
  - **BV2.17** (delete sidecar `/containers/*` aliases) needs **FV2.8** to ship first.

## Working agreement

- After each phase, write a debrief at `team/claude/debriefs/MM/DD__{phase}.md`; index it in `team/claude/debriefs/index.md`.
- If you hit a blocker, surface it in the PR description and stop. Do not rewrite the phase file unilaterally — flag for human ratification.
- If you find a gap not covered by any phase file, add it to the backlog at `team/roles/librarian/DAILY_RUN.md` (B-XXX); do not address it in the current PR.

---

Begin by reading the seven files in section "Your first 30 minutes" above, then `BV2_1__delete-orphan-host.md`, then start the work. Ship one PR. Wait.
