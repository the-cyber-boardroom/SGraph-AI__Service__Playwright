---
title: "Content-transformation proxy — Testing strategy"
file: 05__testing-strategy.md
author: Architect (Claude)
date: 2026-06-18
version: v0.2.63
status: PROPOSED — per-piece first, then integration. TUI-driveable. No mocks.
---

# Testing strategy

The owner's requirement: **test each piece of the puzzle in isolation, then their
integration**, and have **TUI support** so a human can watch/drive the tests. This mirrors the
Sentinel model (per-component + a parity matrix + a traffic corpus + TUI surfaces).

**Rules:** no mocks, no patches; in-memory composition + `_Fake_*` subclasses; assert on
contracts (schemas, status codes, headers, persisted artefacts); real Chromium gated on
`SG_PLAYWRIGHT__CHROMIUM_EXECUTABLE` (skip cleanly when absent).

---

## The test pyramid

```
        ┌───────────────────────────────────────────┐
        │  deploy-via-pytest (EC2 lifecycle)         │   gated on creds
        ├───────────────────────────────────────────┤
        │  integration: the TWO deliverable paths    │   gated on chromium + docker
        ├───────────────────────────────────────────┤
        │  traffic corpus (accuracy + latency)       │   in-process; always runs
        ├───────────────────────────────────────────┤
        │  per-piece units (addon, FastAPI contract, │   always runs, no AWS/docker
        │  compose render, vault loader, TUI renders)│
        └───────────────────────────────────────────┘
```

---

## 1. Per-piece (each puzzle piece alone)

### 1a. The interceptor addon (pure functions, no live mitmproxy)
Build fixture flow objects (a tiny `_Fake_Flow` with `.request`/`.response` mirroring
`mitmproxy.http`). Assert:
- `should_process_request`: GET-only; `/mitm-proxy` always; static extensions skipped; html
  processed.
- `should_process_response`: cached-in-request skipped; non-html skipped; html processed.
- `apply_request_modifications`: header add/remove; `block_request` → 403 made; returns
  block flag.
- `apply_response_modifications`: `override_response`/`modified_body` sets content +
  content-length; header edits; `include_stats`.
- `prepare_request_data` / `prepare_response_data`: shape matches doc 03 (Cookie present;
  body only for text content).

### 1b. The FastAPI MITM contract (against an in-memory stub of the service)
Stand up a `_Fake_Mitm_Service` that implements `/proxy/process-request|response` returning
canned modifications. Drive the addon's `call_fastapi_*` against it (real `urllib`, localhost).
Assert: connected vs unavailable (`x-proxy-status`), injected `<script>` lands in
`modified_body`, CSP header removed when the stub asks.

### 1c. Compose render
`ContentProxy__Compose__Template.render(...)` → assert: **two** mitmproxy services; `ext` has
`--proxyauth`, `int` does not; both have `--scripts` + the three `FASTAPI_*` env; sg-playwright
points at `mitmproxy-int:8081` + `IGNORE_HTTPS_ERRORS`; mitm-service `:10011`; net-local ports
(8081/10011/8000) not published externally.

### 1d. Vault loader
`ContentProxy__Vault__Loader` with a `_Fake_Vault_Store`: `ZIP` copy-in lands files; `SGIT`
clone invoked with the right ref (assert the command builder; no network). Vault keys never in
fixtures.

### 1e. Health probe
`ContentProxy__HTTP__Probe` against `_Fake` endpoints → `Schema__Content_Proxy__Stack__Info`
with per-component health.

### 1f. TUI renders (pure)
Feed each `*__Render` fn a known schema → assert the rendered table/panel content. Headless
screen smoke (Textual pilot, sentinel `test_screens_pilot`/`test_renders` pattern). Assert the
`--json` and no-TTY plain fallbacks for every command.

---

## 2. The traffic corpus (accuracy — the "is the transform correct" test)

Mirror `…/sentinel/traffic/`. A labelled corpus under `traffic/corpus/`:

```
  page                         label            expectation
  ───────────────────────────  ───────────────  ─────────────────────────────
  pii_table.html               should-blur      salary cells blurred
  tracking_pixel.html          should-remove    pixel node removed
  banned_host (news.bad/)      should-block     403 from the proxy
  plain_article.html           should-pass      unchanged (no rules fire)
  static_bundle.js             should-skip      never sent to FastAPI
```

`ContentProxy__Traffic__Runner` replays the corpus through the workflow (in-process against
the addon + the in-memory MITM stub for unit-level; through real containers for integration).
`…__Report__Builder` reports **accuracy** (blurred/removed/blocked as labelled, false-positive
on should-pass) + **latency** percentiles. This is the regression gate when a script changes.

```
  ┌─ traffic report ───────────────────────────────────────────┐
  │ should-blur    4/4   ✓     should-pass   6/6   ✓ (0 FP)     │
  │ should-remove  3/3   ✓     should-skip   9/9   ✓            │
  │ should-block   2/2   ✓     p50 38ms  p95 120ms              │
  └────────────────────────────────────────────────────────────┘
```

Driveable from the TUI `transform`/`traffic` screens (the human watches it run).

---

## 3. Integration — the two deliverables (the whole point)

Real docker-compose (or testcontainers) + real Chromium, both gated.

- **AC-1 (deliverable a):** browser/curl with proxy `http://USER:PASS@host:8080` →
  transformed page; wrong/no creds → 407; CA trust documented.
- **AC-2 (deliverable b):** `sg-playwright /sequence/execute` with browser proxied to
  `mitmproxy-int:8081`, `mitm-*` cookies set → extracted DOM/text shows the transform;
  screenshot diff. Same script/result as AC-1 (assert parity).

**Parity assertion:** the same corpus URL through `ext` and through `int` yields the same
transform (one workflow, two doors). Mirror Sentinel's parity matrix.

---

## 4. deploy-via-pytest (EC2 lifecycle, gated on creds)

Numbered, top-down:

```
test_1__create_stack
test_2__components_health        # ext, int, mitm-service, sg-playwright, vault-app
test_3__load_vaults              # zip + sgit; active script present
test_4__transform_via_ext        # AC-1 live
test_5__transform_via_int        # AC-2 live (sg-playwright)
test_6__logs_append_to_s3        # role 2: reopen the log vault elsewhere
test_7__delete_stack
```

---

## 5. CI placement

Per-piece + traffic corpus + TUI render tests run in the unified `run-unit-tests` job (no
docker/creds). Integration + deploy-via-pytest gated (chromium / docker / AWS) and skip cleanly
when the gate env is absent — same convention as the Sentinel and Playwright suites.

---

## 6. The TUI as a test surface (the owner's "TUI support" ask)

The TUI is a **GUI over the CLI**, and the CLI is fully `--json`-driveable, so the same calls
the human clicks are the calls pytest makes:

- `sp content-proxy transform <url> --json` → the structured before/after CI asserts.
- `sp content-proxy traffic --run-corpus --json` → the accuracy report CI asserts.
- `sp content-proxy status --json` → component health CI asserts.

A human runs `sp content-proxy tui` to watch the same data live; CI runs the `--json` variants
headless. One source of truth, two consumers (the Sentinel principle).
</content>
