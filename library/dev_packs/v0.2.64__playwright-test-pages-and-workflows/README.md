---
title: "Playwright Test Pages & Workflows — Dev Briefing Pack"
file: README.md
author: Architect (Claude)
date: 2026-06-21
repo: "SGraph-AI__Service__Playwright @ dev (root version: v0.2.63; this pack: v0.2.64 — forward-looking)"
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
turns that gap into a buildable backlog. It builds the console on the shared
sgraph.ai component library (`sg-layout` + `sg-tool-api` + sg-tokens, consistent
with the admin dashboard at
`sgraph_ai_service_playwright__api_site/admin/index.html:19,7`) and reorganises
it around the service's own `/health/capabilities` self-description so the UI
never advertises a surface a given deployment lacks. Because the page now loads
served components and asset URLs, **all asset/component/fetch URLs are
root_path-aware** so the console works identically behind the `/pw` reverse proxy
and standalone at root (brief 08). Phase 1 is cheap, high-value
bug-fixes (the health badge that always reads "degraded" because it sends no key;
the unescaped `${url}` lightbox injection; missing null guards) plus wiring
`/health/capabilities`. Later phases add a sequence builder, a portable-JSON
workflow format that round-trips with `/sequence/execute`, in-app docs generated
from the live capability surface, an agentic `window.__tool` JS API registered via
the real `sg-tool-api` component, and an integration-test tier that maps each
example workflow to an assertion and whose Docker image checks gate the Docker Hub
publish. The whole thing is sequenced as a 7-phase, multi-agent orchestration in
`07__implementation-plan.md`.

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
| 05 | [`05__js-api.md`](05__js-api.md) | **(f)** PROPOSED agentic `window.__tool` JS API, aligned to the sgraph.ai house pattern (Q1 + Q1b RESOLVED → registered via the real `sg-tool-api` component). |
| 06 | [`06__integration-tests.md`](06__integration-tests.md) | **(g)** No-mocks integration strategy; Docker build + UI execute-path smoke; per-workflow assertions; Docker tests gate the Docker Hub publish |
| 07 | [`07__implementation-plan.md`](07__implementation-plan.md) | Sequenced phases + multi-agent orchestration (lab-harness style) |
| 08 | [`08__proxy-and-components.md`](08__proxy-and-components.md) | **The `/pw` reverse-proxy model + root_path-aware asset/component URLs** (Decision #11). Root_Path__Resolver precedence; component-URL prefix hazard + fix; CDN-vs-vendored-vs-prefixed trade-off + offline/egress consideration |

---

## Locked decisions

These are settled design choices. If any seems wrong, raise an Architect-review
request — do not silently change them.

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | **Build the console on the shared sgraph.ai component library** — `sg-layout` (panel/routing shell) + `sg-tool-api` (the `window.__tool` bridge) + sg-tokens — consistent with the admin dashboard (`sgraph_ai_service_playwright__api_site/admin/index.html:19` uses `<sg-layout id="root-layout">`; `:7` loads `sg-tokens.css` from the CDN). The console is still served from `GET /` (`INDEX_HTML` in `Routes__Index.py`) over same-origin `fetch()`, but it now composes served web components instead of being a single dependency-free file. | **Reverses the rev-1/rev-2 "single self-contained no-deps file" choice** per the operator (2026-06-21): reusing `sg-tool-api`/`sg-layout` brings the powerful shared-component features (dev panels, routing, tokens) and aligns the test page with the rest of the tools. **Consequence:** this trades away the zero-dependency property — the page now depends on those components (and asset URLs) being reachable, which makes Decision #11 (root_path-aware URLs) mandatory so the same Docker image still works on all 5 targets and behind `/pw`. |
| 2 | **The UI is capability-driven.** On load, the page fetches `GET /health/capabilities` + `GET /health/info` and shows/hides/annotates controls from the response (video tab only if `supports_video`, sink picker limited to `supported_sinks`, etc.). No hard-coded "this deployment can do X". | Closes **D6** (capabilities never fetched) at the root. Docs and UI cannot drift from what the deployment actually supports. |
| 3 | **Workflows are portable JSON that matches the `/sequence/execute` request schema** (`Schema__Sequence__Request`) — a workflow file IS a request body plus a thin metadata envelope. Batch workflows match `Schema__Screenshot__Batch__Request`. | A workflow you save in the UI is the exact JSON you'd `curl`. No bespoke DSL, no translation layer, no drift. Round-trips losslessly (brief 03). |
| 4 | **Phase 1 = bug-fixes + `/health/capabilities` wiring only.** The health-badge-no-key bug, the unescaped `${url}` lightbox, the missing `Array.isArray`/null guards, and the "html-is-not-a-screenshot-format" mislabel ship first, before any new capability tab. | Cheapest, highest-confidence value; de-risks the rest; gives downstream agents a clean base. |
| 5 | **Tabs map 1:1 to endpoint families, not to ad-hoc features.** `Screenshot` · `Sequence` (the 24-verb builder) · `Inspect` · `Session` · `Browser` (one-shots) · `Debug` (console+network) · `Service` (health/info/capabilities/metrics). The current Single/Batch live under `Screenshot`. | The map's §7 backlog is organised by endpoint; mirroring it keeps the UI legible and testable per-tab. |
| 6 | **Every UI action exposes "Copy as curl" and "Copy as JSON".** The request the UI builds is always inspectable and portable; it equals the workflow file format (Decision #3). | Pairs the UI with the consumer-skill curl recipes; makes the UI self-documenting and test-seedable. |
| 7 | **Auth-mode toggle: `X-API-Key` (direct) vs `x-sgraph-access-token` (`/pw` proxy).** The console offers both, defaulting to direct; the health badge and every request reuse the selected mode + entered key. | Matches the two real deployment paths in `use-sg-playwright/SKILL.md`; fixes the badge bug (Decision #4) by reusing the key instead of sending none. |
| 8 | **The JS API follows the agentic `window.__tool` house pattern** (precedent supplied 2026-06-21: `sgraph.ai/.../agentic-js-api`). The console becomes a dual-surface, self-describing `window.__tool` whose `meta.getSkills()` is generated from the code-derived capability surface. **Q1b RESOLVED → option (A):** `window.__tool` is registered via the **real `sg-tool-api` web component** (not an inline shim), wired alongside `sg-layout` per Decision #1. | Q1 + Q1b both resolved; designing blind is no longer a risk. Using the real `sg-tool-api` brings the explorer/console/manifest dev panels for free and keeps the contract identical to every other sgraph.ai tool. The dual-surface pattern also closes D2/D4 (docs served by the implementation never drift). |
| 9 | **No new runtime endpoints, no schema changes, no new step verbs.** This pack is UI + workflow-format + docs + tests against the **existing** 21-endpoint / 24-verb surface. Any "we need a new verb" finding becomes a feature request in a *future* pack, not this one. | Keeps blast radius bounded; the service surface is already rich enough to warrant a far better UI before adding more. |
| 10 | **Markdown deliverables use YAML frontmatter, never `# ═══` headers.** | CLAUDE.md rule #7 — `# ═══` renders as stacked H1s on GitHub. |
| 11 | **All asset/component/fetch URLs are root_path-aware; the console must work identically behind `/pw` and at root.** Component/asset URLs must either be templated with the resolved root_path prefix (the way `window.API_BASE` already is — `Routes__Index.py:26`/`:613-614`, `Root_Path__Resolver.py:41-53`) **or** be loaded CDN-absolute from `https://dev.tools.sgraph.ai/...` (prefix-independent but requires browser egress to that host). Absolute-rooted URLs like `/components/...` or `/api/specs/...` are forbidden — they resolve to `host/components/...`, not `host/pw/components/...`, and break behind the proxy. | Decision #1 made the page load served components; the sg-send-vault-app proxies `/pw/*` to this service (live: `https://crisp-pascal.sg-compute.sgraph.ai/pw/`). `fetch()` is already prefix-safe via `window.API_BASE`; the new component/asset URLs must be too. Captures the offline/egress trade-off (CDN host unreachable on a locked-down deployment → must vendor or prefix-template). See brief 08. |

---

## Open questions

| # | Question | Why it matters | Recommended default |
|---|----------|----------------|---------------------|
| **Q1** | ✅ **RESOLVED (2026-06-21).** JS-API precedent supplied: the agentic JS-API house pattern at `sgraph.ai/.../use-cases/agentic-js-api` (`window.__tool` + `meta.getSkills()`, dual-surface, self-describing). The rev-1 `SgPlaywrightClient` HTTP-wrapper guess is superseded. | Brief 05 (rev 2) now designs against the real pattern. | Done — see brief 05 rev 2 and `agentic-js-api-research.md`. |
| **Q1b** | ✅ **RESOLVED (2026-06-21) → option (A).** Register `window.__tool` via the shared `sg-tool-api` web component (served, consistent with other tools, free dev panels) — **chosen** — rather than an inline shim. Operator: reuse the shared component AND build on `sg-layout`. | (A) introduces a served-component dependency + asset-URL serving path (now handled by Decision #11 / brief 08); the dropped no-deps property is the deliberate trade for the shared-component features. | Done — see Decision #1, Decision #8, brief 05 rev 3 §6/§8. The consequence (root_path-aware asset URLs) is Decision #11 + brief 08. |
| Q2 | Should the console persist workflows to localStorage only, or also offer a server-side "saved workflows" store? | Affects whether brief 03 needs any backend (it currently designs **zero** backend — localStorage + file up/download only). | Client-only (localStorage + file). No backend. Server-side store is a future pack. |
| Q3 | Does the JS allowlist get a UI affordance, or stay deny-all-invisible? `evaluate` and `wait_for: function` fail with "allowlist" not 422. | A first-time user running `evaluate` in the builder will see a confusing `partial` status. | Brief 01: show an inline "this step needs the server JS allowlist" hint on `evaluate`/`wait_for:function`; do not attempt to mutate the allowlist from the UI. |
| Q4 | Capture-sink picker — expose all four sinks (`VAULT`/`S3`/`LOCAL_FILE`/`INLINE`) or only those in `supported_sinks`? | Showing `VAULT` on a deployment without vault access produces silent failures. | Per Decision #2 — limit the picker to `capabilities.supported_sinks`; default `INLINE`. |
| Q5 | ✅ **RESOLVED (2026-06-21).** Where do the Docker-dependent integration tests sit in CI? | Operator: the Docker integration checks must **gate publication** — run them after the image build and before the Docker Hub publish. | The CI pipeline (`.github/workflows/ci-pipeline.yml`) **already implements this shape:** `build-amd64`/`build-arm64` (`:123,:181`) build + push **by digest only** (no tag), then `integration-test-image` (`:254`) runs the live suite against the by-digest amd64 image, and `push-playwright-manifest` (`:400`) only tags + publishes to Docker Hub when `needs.integration-test-image.result == 'success'` (`:404-405`). The pack's new W1/capabilities Docker smoke checks (brief 06 §5) extend the `integration-test-image` job so they too gate the publish. See 06. |

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
   pattern, registered via the real `sg-tool-api` component on `sg-layout`) is
   documented and implementable without re-architecting — its `meta.getSkills()`
   is generated from the live capability surface, so the page is self-describing
   to agents and its docs cannot drift.
9. **Integration tests** map each gallery workflow to an assertion, gate real
   Chromium on `SG_PLAYWRIGHT__CHROMIUM_EXECUTABLE`, skip cleanly when absent, use
   no mocks/patches, and the Docker-image integration checks run after the image
   build and **gate the Docker Hub publish** (a red check blocks the manifest tag).
10. **The console works identically behind `/pw` and at root** — every
    asset/component/fetch URL is root_path-aware (Decision #11, brief 08).

---

## Critical-path sign-off (Architect → Dev)

Before any downstream agent picks up a slice:

- [ ] All 11 locked decisions accepted
- [x] **Q1 (JS-API precedent) answered** — agentic `window.__tool` pattern supplied; brief 05 aligned
- [x] **Q1b (sg-tool-api component vs inline shim)** ruled on by the operator → **option (A): reuse the real `sg-tool-api` component on `sg-layout`** (reverses old Decision #1); see Decision #1, #8, brief 05 rev 3, brief 08
- [x] **Q5 (Docker integration tests in CI)** ruled on → run after image build, **gate the Docker Hub publish** (extend the existing `integration-test-image` job that already gates `push-playwright-manifest`); see brief 06 §5
- [ ] Q2-Q4 ruled on by the operator
- [ ] **Decision #11 / brief 08 accepted** — all asset/component/fetch URLs root_path-aware; console works behind `/pw` and at root
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
| 2026-06-21 | **Rev 3 — operator feedback (4 changes).** (1) **Q1b → option (A):** reuse the shared `sg-tool-api` component AND build the console on `sg-layout` — reverses old Decision #1 ("single self-contained no-deps file") to "build on the shared sgraph.ai component library". Decisions #1, #8 rewritten; brief 05 rev 3 (packaging conclusion now "real `sg-tool-api` on `sg-layout`", §1-§5 unchanged); the "single-file/no-deps" assumption swept out of README, briefs 01 and 07. (2) **`/pw` reverse-proxy + asset prefixing:** new Decision #11 + new brief 08 — all asset/component/fetch URLs root_path-aware (cite `Root_Path__Resolver.py:41-53`, `Routes__Index.py:26,:613-614`, admin `index.html:7,19`); console works behind `/pw` and at root; CDN-vs-vendored-vs-prefixed offline/egress trade-off captured. (3) **Docker tests gate publish (Q5):** brief 06 §5 + README Q5 + plan G6 — the existing `ci-pipeline.yml` already runs `integration-test-image` (`:254`) after `build-amd64`/`build-arm64` and gates `push-playwright-manifest` (`:400-405`); the pack's Docker smoke checks extend that job. Real CI job names confirmed (no DevOps TODO needed). (4) **YAML frontmatter fix:** all 9 `repo:` lines quoted (the `(root version: ...)` colon broke GitHub's YAML parser). |
