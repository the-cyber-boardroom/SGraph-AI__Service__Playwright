# Frontend session kickoff — paste this into a fresh Claude Code session

You are the **v0.2.x frontend Sonnet team** for SG/Compute. Read this in full before doing anything.

---

## Your identity

- **Repo:** `the-cyber-boardroom/SGraph-AI__Service__Playwright` @ `v0.2.0` (just merged to main)
- **Branch base:** `dev`
- **Counterpart:** a parallel **backend** Sonnet team running in another session — coordinate via the briefs, not directly

## Your first 30 minutes — read in this order

1. `.claude/CLAUDE.md` — project rules
2. `team/comms/briefs/v0.2.0__sg-compute__architecture/00__README.md` — vision + ratified decisions
3. `team/comms/briefs/v0.2.0__sg-compute__architecture/01__architecture.md` — taxonomy, two-package split, spec contract
4. `team/comms/briefs/v0.2.0__sg-compute__architecture/02__node-anatomy.md` — why `linux` was dropped; AMI + Docker + sidecar baseline
5. `team/comms/briefs/v0.2.0__sg-compute__architecture/03__sidecar-contract.md` — first-class sidecar (you talk to it via iframe + via the control plane)
6. `team/comms/briefs/v0.2.0__sg-compute__architecture/sources/code-review-synthesis.md` — distilled findings (6 hardcoded plugin lists, state-vocab bug, A11y gaps, etc.)
7. **Your folder:** `team/comms/briefs/v0.2.0__sg-compute__frontend/00__README.md` — phase index + cross-cutting rules

## Recommended execution order

```
FV2.1 → FV2.2 → FV2.3 → FV2.4 → FV2.7 → FV2.8 → FV2.5 → FV2.6 → FV2.9 →
FV2.10 → FV2.11 → FV2.12   (FV2.13 deferred to v0.3)
```

Why: FV2.1 fixes a latent bug (small, unblocked); FV2.2 unblocks the next 4 phases; FV2.3 kills 6 hardcoded plugin lists; FV2.7-FV2.8 are tightly paired and unlock backend BV2.17; FV2.5 / FV2.6 are larger blocks of work; FV2.9-FV2.11 are quality + cleanup; FV2.12 is the cosmetic prefix sweep.

## Your first phase: **FV2.1 — Centralise node-state vocabulary**

File: [`FV2_1__state-vocabulary-fix.md`](FV2_1__state-vocabulary-fix.md). Latent bug: 6 sites in `sp-cli-nodes-view.js` hardcode `state === 'running'`. Once backend returns `'ready'` or `'READY'`, boot-log polling never stops, row colour breaks, auto-tab-switch never fires. Centralise in `shared/node-state.js`. Small, unblocked.

**Stop after FV2.1.** Wait for the human to ratify and tell you which phase to do next.

## Hard rules (binding every session)

- **No build toolchain.** Native ES modules. Plain CSS. Web Components with Shadow DOM.
- **Three-file pattern**: `.js` + `.html` + `.css` siblings under `{name}/v0/v0.1/v0.1.0/`.
- **Custom-element naming:** keep `sp-cli-*` for now. **FV2.12** renames to `sg-compute-*` after FV2.9 — do NOT rename early.
- **Events on `document`** with `{ bubbles: true, composed: true }`. Listener lives in `admin/admin.js`.
- **Accessibility:** WCAG AA contrast, keyboard nav, ARIA labels on icon-only controls. **FV2.10** is the formal pass; do not regress in earlier phases.
- **No emoji** in source files unless the existing convention uses them (plugin card icons stay).
- **No third-party calls** from the dashboard. **FV2.11** removes the existing `api.ipify.org` call; do not add new ones.
- **Branch:** `claude/fv2-{N}-{description}-{session-id}`. Never push to `dev` directly.
- **PR title:** `phase-FV2.{N}: {short summary}`.
- **PR description:** link to the phase file; list checked acceptance criteria.
- **One phase per PR. One PR per session.**
- **CLAUDE.md rule 9** (no underscore-prefix for private methods) applies **Python only**. JS keeps `_foo()` convention.

## Coordination signals you may receive

- **Backend phases that block yours:**
  - **FV2.5** (launch flow with three creation modes) waits on **BV2.5** (`POST /api/nodes` + `EC2__Platform.create_node`).
  - **FV2.7** (Pods tab via unified URL) waits on **BV2.3** (`Pod__Manager` + `Routes__Compute__Pods`).
  - **FV2.6** (per-spec UI co-location) needs an Architect lock on UI-serving mechanism.
- **Backend phases that depend on yours:**
  - **BV2.17** (delete sidecar `/containers/*` aliases) waits on **FV2.8** to verify zero `/containers/*` URLs in the dashboard.

## Working agreement

- After each phase, write a debrief at `team/claude/debriefs/MM/DD__{phase}.md`; index it.
- If you hit a blocker (e.g. backend hasn't shipped a prerequisite), surface it in the PR description and stop. Don't half-implement.
- If you find a gap not covered by any phase file, add it to `team/roles/librarian/DAILY_RUN.md` backlog; do not silently expand the current phase.

## Two important context items the audit surfaced

- The dashboard talks to **two backends**: the control plane (`Fast_API__Compute` at `/api/*`) and **each Node's sidecar** (at `http://{public_ip}:19009`). Sidecar is reached **directly via iframe** for Terminal + Host API tabs (cookie auth pattern), and **via the control plane** for everything else (after FV2.7).
- `host_api_url` is **derived on the frontend** from `public_ip`: `http://{public_ip}:19009`. `Schema__Node__Info` does not carry it.

---

Begin by reading the seven files in section "Your first 30 minutes" above, then `FV2_1__state-vocabulary-fix.md`, then start the work. Ship one PR. Wait.
