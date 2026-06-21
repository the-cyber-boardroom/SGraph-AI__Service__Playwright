---
title: "Playwright Test Pages & Workflows — Dev Briefing Pack"
file: README.md
author: Architect (Claude)
date: 2026-06-21
repo: SGraph-AI__Service__Playwright @ dev (root version: v0.2.63; this pack: v0.2.64 — forward-looking)
status: PROPOSED — no code yet. Design only. For human ratification before Dev picks up.
feature_branch: claude/amazing-pasteur-3srh6x
---

# Playwright Test Pages & Workflows — Dev Briefing Pack

A design pack for rebuilding the sg-playwright default **"Try it out"** test page
(`INDEX_HTML` in `Routes__Index.py`) from a two-tab screenshot toy into a
**capability-driven console** that exposes the full service surface — the 24-verb
`/sequence` language, `/inspect`, `/session/*`, `/browser/*`, PDF, DOM/a11y/text/html
extraction, a debug panel, and the live `/health/capabilities` self-description —
plus a portable workflow format, in-app docs, a proposed JS API, and an
integration-test strategy that smoke-tests both the Docker build and the UI's
execute paths.

> **PROPOSED — does not exist yet.** No UI, workflow, JS-API, or test code in this
> pack. The only diff this pack produces is its own markdown files plus a one-line
> entry in `library/dev_packs/README.md`. `INDEX_HTML` and all runtime code are
> untouched. Downstream Dev sessions implement; this pack designs.

---

## One-paragraph summary

The capability map the Dev produced on 2026-06-21
(`team/humans/dinis_cruz/claude-code-web/06/21/15/playwright-capability-map.md`)
proved the test page exposes only `/screenshot` + `/screenshot/batch` — a thin
slice of a **21-direct-endpoint, 24-verb** service (discrepancy **D5**). This pack
turns that gap into a buildable backlog. It keeps the single self-contained
HTML/JS file pattern (one route, same-origin, no build step) but reorganises it
around the service's own `/health/capabilities` self-description so the UI never
advertises a surface a given deployment lacks. Phase 1 is cheap, high-value
bug-fixes (the health badge that always reads "degraded" because it sends no key;
the unescaped `${url}` lightbox injection; missing null guards) plus wiring
`/health/capabilities`. Later phases add a sequence builder, a portable-JSON
workflow format that round-trips with `/sequence/execute`, in-app docs generated
from the live capability surface, a proposed JS SDK + `window.*` programmable
console API, and an integration-test tier that maps each example workflow to an
assertion. The whole thing is sequenced as a 7-phase, multi-agent orchestration
in `07__implementation-plan.md`.

---

## Source documents

| Source | Authority | Use for |
|--------|-----------|---------|
| `team/humans/dinis_cruz/claude-code-web/06/21/15/playwright-capability-map.md` | **Code-derived capability map — the ground truth.** | Every endpoint, schema, step verb, default, and the D1-D6 discrepancies. If this pack and the reality doc disagree, **the code (and this map) wins.** |
| `library/skills/sg-playwright-capabilities/SKILL.md` | **Code-derived field-by-field lookup.** | Exact request/response shapes, enum values, result-field-by-verb table. The pack's docs brief (04) generates from the same surface. |
| `library/skills/use-sg-playwright/SKILL.md` | **Accurate consumer recipes + auth split.** | The 5 worked recipes seed the example gallery (02); the auth-header table drives the auth-mode toggle (01). |
| `library/dev_packs/v0.2.9__improve-playwritght-api/` (3 briefs) | Prior Playwright pack — closest precedent. | Tone + feature-request format. **Cross-checked:** its requested `wait`, `wait_for: function`, `scroll`, `get_content` verbs now EXIST (see `00__capability-baseline.md`). |
| `sg_compute_specs/playwright/core/fast_api/routes/Routes__Index.py` | The artefact being improved. | `INDEX_HTML` lines 20-601 — current tabs, bugs, the `__API_BASE__` injection seam. |
| `sg_compute_specs/playwright/core/schemas/enums/Enum__Step__Action.py` | The 24-verb vocabulary (authoritative). | Verb names cited verbatim in 02. |
| `https://sgraph.ai/.../use-cases/agentic-js-api` (+ `.md` per page) | **The agentic JS-API house pattern — supplied by operator 2026-06-21.** | `window.__tool` + `meta.getSkills()` dual-surface design that brief 05 aligns to. Resolves Q1. |
| `team/humans/dinis_cruz/claude-code-web/06/21/15/agentic-js-api-research.md` | Captured grounding of the above (offline-readable). | The `window.__tool` surface, `getSkills()` trio, `sg-tool-api` component, Playwright runtime-discovery workflow. |

If this pack contradicts any of those, **the source wins** — open an Architect-review
request, do not silently diverge.

---

## File index

| # | File | Purpose |
|---|------|---------|
| 00 | this README | Status, locked decisions, open questions, sign-off |
| 00 | [`00__capability-baseline.md`](00__capability-baseline.md) | What exists today, UI-exposed vs omitted, D1-D6 the pack must not re-introduce |
| 01 | [`01__proposed-ux-pages.md`](01__proposed-ux-pages.md) | **(a)** Capability-driven console — tabs, panes, per-capability UI, the real bug-fixes, ASCII wireframes |
| 02 | [`02__workflow-examples.md`](02__workflow-examples.md) | **(b)** Gallery of complex `/sequence/execute` JSON workflows; double as gallery seeds + test fixtures |
| 03 | [`03__workflow-authoring.md`](03__workflow-authoring.md) | **(c)** Portable-JSON import/export, localStorage, file up/download, copy-as-curl, round-trip guarantees |
| 04 | [`04__docs-and-help.md`](04__docs-and-help.md) | **(d)** In-app docs generated from `/health/capabilities` + step surface; contextual help; `/docs` deep-links |
| 05 | [`05__js-api.md`](05__js-api.md) | **(f)** PROPOSED agentic `window.__tool` JS API, aligned to the sgraph.ai house pattern (Q1 RESOLVED). One sub-decision remains (Q1b: component reuse vs inline shim). |
| 06 | [`06__integration-tests.md`](06__integration-tests.md) | **(g)** No-mocks integration strategy; Docker build + UI execute-path smoke; per-workflow assertions |
| 07 | [`07__implementation-plan.md`](07__implementation-plan.md) | Sequenced phases + multi-agent orchestration (lab-harness style) |

---

## Locked decisions

These are settled design choices. If any seems wrong, raise an Architect-review
request — do not silently change them.

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | **Keep the single self-contained HTML/JS file pattern.** One route (`GET /`), `INDEX_HTML` string in `Routes__Index.py`, same-origin `fetch()`, no build step, no external deps, no CORS. The console grows inside that file. | Matches `Routes__Index.py:6-9` design intent ("no external deps", "same origin so fetch() calls don't need CORS"). Lambda/Fargate/laptop parity needs zero asset pipeline. |
| 2 | **The UI is capability-driven.** On load, the page fetches `GET /health/capabilities` + `GET /health/info` and shows/hides/annotates controls from the response (video tab only if `supports_video`, sink picker limited to `supported_sinks`, etc.). No hard-coded "this deployment can do X". | Closes **D6** (capabilities never fetched) at the root. Docs and UI cannot drift from what the deployment actually supports. |
| 3 | **Workflows are portable JSON that matches the `/sequence/execute` request schema** (`Schema__Sequence__Request`) — a workflow file IS a request body plus a thin metadata envelope. Batch workflows match `Schema__Screenshot__Batch__Request`. | A workflow you save in the UI is the exact JSON you'd `curl`. No bespoke DSL, no translation layer, no drift. Round-trips losslessly (brief 03). |
| 4 | **Phase 1 = bug-fixes + `/health/capabilities` wiring only.** The health-badge-no-key bug, the unescaped `${url}` lightbox, the missing `Array.isArray`/null guards, and the "html-is-not-a-screenshot-format" mislabel ship first, before any new capability tab. | Cheapest, highest-confidence value; de-risks the rest; gives downstream agents a clean base. |
| 5 | **Tabs map 1:1 to endpoint families, not to ad-hoc features.** `Screenshot` · `Sequence` (the 24-verb builder) · `Inspect` · `Session` · `Browser` (one-shots) · `Debug` (console+network) · `Service` (health/info/capabilities/metrics). The current Single/Batch live under `Screenshot`. | The map's §7 backlog is organised by endpoint; mirroring it keeps the UI legible and testable per-tab. |
| 6 | **Every UI action exposes "Copy as curl" and "Copy as JSON".** The request the UI builds is always inspectable and portable; it equals the workflow file format (Decision #3). | Pairs the UI with the consumer-skill curl recipes; makes the UI self-documenting and test-seedable. |
| 7 | **Auth-mode toggle: `X-API-Key` (direct) vs `x-sgraph-access-token` (`/pw` proxy).** The console offers both, defaulting to direct; the health badge and every request reuse the selected mode + entered key. | Matches the two real deployment paths in `use-sg-playwright/SKILL.md`; fixes the badge bug (Decision #4) by reusing the key instead of sending none. |
| 8 | **The JS API follows the agentic `window.__tool` house pattern** (precedent supplied 2026-06-21: `sgraph.ai/.../agentic-js-api`). The console becomes a dual-surface, self-describing `window.__tool` whose `meta.getSkills()` is generated from the code-derived capability surface. One sub-decision remains (Q1b): reuse the shared `sg-tool-api` web component vs. an inline shim — Architect recommends the inline shim to preserve the no-deps single-file invariant. | Q1 is resolved; designing blind is no longer a risk. The dual-surface pattern also closes D2/D4 (docs served by the implementation never drift). |
| 9 | **No new runtime endpoints, no schema changes, no new step verbs.** This pack is UI + workflow-format + docs + tests against the **existing** 21-endpoint / 24-verb surface. Any "we need a new verb" finding becomes a feature request in a *future* pack, not this one. | Keeps blast radius bounded; the service surface is already rich enough to warrant a far better UI before adding more. |
| 10 | **Markdown deliverables use YAML frontmatter, never `# ═══` headers.** | CLAUDE.md rule #7 — `# ═══` renders as stacked H1s on GitHub. |

---

## Open questions

| # | Question | Why it matters | Recommended default |
|---|----------|----------------|---------------------|
| **Q1** | ✅ **RESOLVED (2026-06-21).** JS-API precedent supplied: the agentic JS-API house pattern at `sgraph.ai/.../use-cases/agentic-js-api` (`window.__tool` + `meta.getSkills()`, dual-surface, self-describing). The rev-1 `SgPlaywrightClient` HTTP-wrapper guess is superseded. | Brief 05 (rev 2) now designs against the real pattern. | Done — see brief 05 rev 2 and `agentic-js-api-research.md`. |
| **Q1b** | **Component reuse vs. inline shim (sub-decision of Q1).** Register `window.__tool` via the shared `sg-tool-api` web component (served from `/components/...`, consistent with other tools, free dev panels) **or** inline a contract-identical minimal shim in `INDEX_HTML`? | (A) introduces an external component dependency + serving path; (B) preserves the single-file/no-build invariant (Decision #1) that lets one Docker image run on all 5 targets. | **(B) inline shim**, contract byte-identical to `sg-tool-api` so a later swap to (A) is transparent. Adopt (A) only if the test page is allowed served components. |
| Q2 | Should the console persist workflows to localStorage only, or also offer a server-side "saved workflows" store? | Affects whether brief 03 needs any backend (it currently designs **zero** backend — localStorage + file up/download only). | Client-only (localStorage + file). No backend. Server-side store is a future pack. |
| Q3 | Does the JS allowlist get a UI affordance, or stay deny-all-invisible? `evaluate` and `wait_for: function` fail with "allowlist" not 422. | A first-time user running `evaluate` in the builder will see a confusing `partial` status. | Brief 01: show an inline "this step needs the server JS allowlist" hint on `evaluate`/`wait_for:function`; do not attempt to mutate the allowlist from the UI. |
| Q4 | Capture-sink picker — expose all four sinks (`VAULT`/`S3`/`LOCAL_FILE`/`INLINE`) or only those in `supported_sinks`? | Showing `VAULT` on a deployment without vault access produces silent failures. | Per Decision #2 — limit the picker to `capabilities.supported_sinks`; default `INLINE`. |
| Q5 | Does the deploy/CI tier get a real `docker build` job, or only the wheel/UI-snapshot test that exists today? | Brief 06 point (a) asks for a Docker-build test; no `docker build` test exists today (only `test_wheel_contains_ui.py` + compose-template rendering). | Add a `workflow_dispatch`-gated CI job that builds the image and curls `GET /` + `/health/capabilities`; keep it off the per-PR path (slow). See 06. |

---

## What success looks like

When this milestone closes:

1. **Opening `GET /`** on any deployment shows a console whose visible controls
   match that deployment's `/health/capabilities` — no dead buttons.
2. **The health badge reads "healthy"** on a key-protected deployment (Phase-1 bug
   fixed — it reuses the entered key instead of sending none).
3. A user can **build and run a multi-step `/sequence/execute`** workflow from the
   UI, see per-step results, and capture a screenshot per step.
4. **`/inspect`, `/session/*`, `/browser/*`, PDF, DOM/a11y/text/html, and the
   console+network debug panel** are all reachable from the UI.
5. Any UI request can be **exported as a workflow JSON file**, re-imported, and
   produces the identical request (lossless round-trip), and **copied as curl**.
6. **In-app docs** list every step verb + its fields, generated from the live
   capability surface, so they cannot drift from D2/D4.
7. The **example gallery** loads ≥6 complex workflows (brief 02) with one click.
8. A **proposed agentic JS API** (`window.__tool`, aligned to the sgraph.ai house
   pattern) is documented and implementable without re-architecting — its
   `meta.getSkills()` is generated from the live capability surface, so the page is
   self-describing to agents and its docs cannot drift.
9. **Integration tests** map each gallery workflow to an assertion, gate real
   Chromium on `SG_PLAYWRIGHT__CHROMIUM_EXECUTABLE`, skip cleanly when absent, use
   no mocks/patches, and a Docker-build job curls the live `GET /`.

---

## Critical-path sign-off (Architect → Dev)

Before any downstream agent picks up a slice:

- [ ] All 10 locked decisions accepted
- [x] **Q1 (JS-API precedent) answered** — agentic `window.__tool` pattern supplied; brief 05 rev 2 aligned
- [ ] **Q1b (sg-tool-api component vs inline shim)** ruled on — Architect recommends inline shim; gates brief 05 Phase 5 only
- [ ] Q2-Q5 ruled on by the operator
- [ ] `00__capability-baseline.md` cross-checked against the capability map (code wins on any conflict)
- [ ] `07__implementation-plan.md` agent boundaries confirmed independent
- [ ] Confirmed: **no runtime code, no `INDEX_HTML`, no schema, no reality-doc edits** land from this pack — only the UI/workflow/test work the downstream phases produce
- [ ] Librarian notified that the reality doc is stale on endpoint count + `Routes__Session` (D1) — tracked, not fixed here
- [ ] AppSec has reviewed the XSS-fix list (unescaped `${url}`, cleartext-key localStorage note) in brief 01

---

## Status updates

| Date | Note |
|------|------|
| 2026-06-21 | Pack filed at `v0.2.64__playwright-test-pages-and-workflows/`. Built on the 2026-06-21 capability map (v0.2.63 code basis). PROPOSED — design only. |
| 2026-06-21 | Brief 05 rev 2 — operator supplied the JS-API precedent (agentic `window.__tool` pattern, `sgraph.ai/.../agentic-js-api`). Q1 RESOLVED; rev-1 `SgPlaywrightClient` guess superseded. New sub-decision Q1b (component reuse vs inline shim; Architect recommends inline shim). README Decision #8, source docs, Q1, sign-off, success criteria updated. |
