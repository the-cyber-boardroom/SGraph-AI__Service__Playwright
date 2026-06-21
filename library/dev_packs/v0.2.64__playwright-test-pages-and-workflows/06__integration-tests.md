---
title: "06 — Integration-test strategy"
file: 06__integration-tests.md
author: Architect (Claude)
date: 2026-06-21
repo: SGraph-AI__Service__Playwright @ dev (root version: v0.2.63)
status: PROPOSED — test design, no test code
parent: README.md
covers: "User point (g) — integration tests for the Docker build and UI workflows"
---

# 06 — Integration-test strategy

Covers **point (g)**: a test strategy that (a) tests the Docker build and (b) invokes
the brief-02 workflows from the UI surface. Follows the repo's testing rules: **no
mocks, no patches**, in-memory composition, real-Chromium gating on
`SG_PLAYWRIGHT__CHROMIUM_EXECUTABLE` with clean skips, deploy-via-pytest numbered
tests.

> **Code-vs-brief discrepancy (code wins).** The mission says compose via
> `register_playwright_service__in_memory()`. **That function does not exist in this
> repo.** The actual in-memory composition pattern is a local `_build_fast_api()`
> helper that injects a `_FakeLauncher()` —
> `tests/unit/fast_api/routes/test_Routes__Screenshot.py:149-154` and
> `test_Routes__Sequence.py:117-121`. This brief uses the real pattern and flags the
> name discrepancy for sign-off. (A future Dev phase MAY add a shared
> `register_playwright_service__in_memory()` fixture to match the house convention;
> if so, the tests below adopt it. Until then, `_build_fast_api()` is the truth.)

---

## 1. The existing test tiers (what we extend, not replace)

| Tier | Path | Gating | Role |
|------|------|--------|------|
| Unit | `tests/unit/` | none — `_FakeLauncher()` | Schema/route contracts without a browser |
| Integration | `tests/integration/` | real Chromium (`SG_PLAYWRIGHT__CHROMIUM_EXECUTABLE` or `playwright install`) | `Step__Executor`, `Browser__Launcher` against real Chromium |
| Live HTTP | `tests/integration_live/` | `SG_PLAYWRIGHT__LIVE_BASE_URL` + `SG_PLAYWRIGHT__LIVE_API_KEY` (skip-gate `conftest.py:65-70`) | black-box HTTP against a running service |
| Local | `tests/local/` | real Chromium (`pytest.skip` when absent) | proxy + credential variants |
| CI snapshot | `tests/ci/test_wheel_contains_ui.py` | none | asserts the UI ships in the wheel |

This pack adds tests in **three** of these tiers: unit (UI request-body builders),
integration (workflows W1-W9 against real Chromium), and a new **deploy/CI** Docker
job.

---

## 2. UI request-body builder tests (unit, no browser)

The console builds JSON bodies (brief 01/03). Those builders are testable without a
browser by asserting the JSON they emit. Because the workflow format IS the request
body (Decision #3), a builder test and an HTTP test share one fixture.

Pattern (mirrors `test_Routes__Screenshot.py:149-154`):

```python
def _build_fast_api():
    service = Fast_API__Playwright__Service(...)   # inject _FakeLauncher()
    service.setup()
    return service

# assert the gallery workflow W3's `request` body posts cleanly and the route
# parses it into Schema__Inspect__Request without raising (contract, not impl).
```

For the UI's JS body-builders, a tiny headless-browser harness (brief 06 §4) loads
`GET /`, drives `window.sgp.exportWorkflow()` (brief 05 §4), and asserts the emitted
body equals the gallery fixture — proving the builder round-trips (brief 03 §2).

---

## 3. Workflow → assertion map (integration, real Chromium)

Each brief-02 gallery workflow becomes one gated integration test. Real Chromium
required; skip cleanly when `SG_PLAYWRIGHT__CHROMIUM_EXECUTABLE` is unset (pattern:
`tests/local/test_L3__local_http_proxy.py` `pytest.skip(...)`). **No mocks.**

| Workflow | Endpoint | Assertion (on the contract) |
|----------|----------|-----------------------------|
| W1 form fill + per-step shots | `/sequence/execute` | `status == completed`; `steps_passed == steps_total`; the two `screenshot` step results each have `artefacts[0].inline_b64` non-empty |
| W2 login then extract | `/sequence/execute` | `get_url` result `url` is non-null; `get_text` result `text` non-empty |
| W3 scrape DOM + a11y | `/inspect` | `probe_results.dom.dom_tree` is a nested object; `probe_results.a11y.accessibility_tree.nodes` is a list |
| W4 render PDF | `/sequence/execute` | the `get_pdf` step result has `artefacts[0].artefact_type == PDF` |
| W5 console + network | `/inspect` | `probe_results.console.console_log` is a list; `probe_results.failures.network_failures` is a list |
| W6 viewport/frame/selector | `/sequence/execute` | three screenshot artefacts; the selector-scoped one has smaller `width` than the full-page one |
| W7 hover/select/press/scroll/evaluate | `/sequence/execute` | `status in {completed, partial}`; the `evaluate` step is `failed` with "allowlist" in `error_message` on a default deny-all deployment (asserts the documented gate) |
| W8 batch (items + steps) | `/screenshot/batch` | `len(screenshots) == len(items)`; each has `screenshot_b64` |
| W9 stateful session | `/session/*` | `open` returns a `session_id` + `expires_in_ms`; `act` returns a `Schema__Sequence__Response`; `probe` returns a `Schema__Inspect__Response`; `close` returns `{closed: true}` |

Assertions are on **schemas / status / persisted artefacts**, never implementation
details (CLAUDE.md testing rule #2). W7 deliberately asserts the allowlist *failure*
as a contract — a good-failure test.

---

## 4. UI execute-path smoke (the "from the UI surface" requirement)

To prove the UI's execute paths work end-to-end (not just the JSON bodies), a
headless-browser smoke test:

1. Starts the in-memory service (`_build_fast_api()`), serves `GET /`.
2. Loads `GET /` in a headless Chromium (the service's own Playwright — dog-fooding;
   gated on `SG_PLAYWRIGHT__CHROMIUM_EXECUTABLE`).
3. Drives `window.sgp.run(window.sgp.loadExample('W1'))` (brief 05 §4) — the same
   programmatic surface a user's "Load example → Execute" click hits.
4. Asserts the result pane renders a step list with the expected passed count and an
   `<img>` whose `src` is a `data:image/png;base64,` URL.

This is the only test that exercises the actual DOM/JS of the console; the rest assert
the request bodies + HTTP contracts. It is the most expensive test, so it is
gated/optional and runs in the integration tier, not per-PR. If the JS-API (`window.sgp`)
is not yet built (Phase 5), this test is skipped with a clear reason; the body-level
tests (§2/§3) still cover the workflows.

---

## 5. Docker build + verb-table drift (deploy/CI tier)

**Docker build job (point (a)).** No `docker build` test exists today (only
`test_wheel_contains_ui.py` + compose-template rendering at
`sg_compute_specs/playwright/tests/test_Playwright__Compose__Template.py`). Add a
**`workflow_dispatch`-gated, deploy-via-pytest** numbered sequence (CLAUDE.md testing
rule #4 — `test_1__`, `test_2__`, ... top-down), off the per-PR path (Q5 default):

```
test_1__build_image           docker build of sg_compute_specs/playwright/Dockerfile
test_2__run_container         start it, wait for health
test_3__get_index             GET /            → 200, body contains "SG Playwright"
test_4__get_capabilities      GET /health/capabilities → 200, Schema__Service__Capabilities shape
test_5__execute_workflow_W1   POST /sequence/execute with W1 → status completed
test_6__teardown              stop + rm container
```

These run real `docker build` + container HTTP, so they are slow and on-demand
(`workflow_dispatch`), matching the lab-harness "never in CI initially; on-demand once
a baseline exists" stance.

**Verb-table drift check (brief 04 §1 stretch).** A cheap unit test asserts the
embedded UI verb table matches `STEP_SCHEMAS`
(`dispatcher/step_schema_registry.py:51-85`) and `Enum__Step__Action` — so the in-app
docs (brief 04) cannot rot. This is the structural defence against a future D4.

---

## 6. Test-file placement

| New tests | Tier path | Gate |
|-----------|-----------|------|
| UI body-builder + workflow-fixture parse | `tests/unit/fast_api/routes/` | none |
| W1-W9 against real Chromium | `tests/integration/` (new `test_Workflows__Gallery.py`) | `SG_PLAYWRIGHT__CHROMIUM_EXECUTABLE` |
| UI execute-path headless smoke | `tests/integration/` | `SG_PLAYWRIGHT__CHROMIUM_EXECUTABLE` + `window.sgp` present |
| Docker build deploy-via-pytest | `tests/ci/` or a new `tests/deploy/` numbered module | `workflow_dispatch` |
| Verb-table drift | `tests/unit/` | none |

All follow CLAUDE.md testing rules: no mocks, no patches; assert on contracts; real
Chromium gated and skipped cleanly when absent; deploy tests numbered and run
top-down.
