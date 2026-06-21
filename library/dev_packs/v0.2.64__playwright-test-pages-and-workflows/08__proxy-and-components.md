---
title: "08 — Proxy model & root_path-aware asset/component URLs"
file: 08__proxy-and-components.md
author: Architect (Claude)
date: 2026-06-21 (rev 3 — new brief)
repo: "SGraph-AI__Service__Playwright @ dev (root version: v0.2.63)"
status: PROPOSED — design only, no runtime code
parent: README.md
covers: "Decision #11 — all asset/component/fetch URLs root_path-aware; console works behind /pw and at root"
---

# 08 — Proxy model & root_path-aware asset/component URLs

Rev 3 (Decision #1) builds the console on the shared sgraph.ai component library
(`sg-layout` + `sg-tool-api` + sg-tokens). That introduces a hazard the old
single-self-contained-file design did not have: **the page now loads served
components and asset URLs, and those URLs must resolve correctly whether the service
is standalone at root or fronted by the `/pw` reverse proxy.** This brief specifies
the proxy model, why `fetch()` is already safe, the new component/asset-URL hazard,
the rule that fixes it, the CDN-vs-vendored-vs-prefixed trade-off (including the
offline/egress consideration), and the acceptance check.

> This brief is the home of **Decision #11**. Briefs 01 and 05 reference it; the
> downstream P2 (component wiring) and P5 (`sg-tool-api`) slices must honour it.

---

## 1. The `/pw` reverse-proxy model

When sg-playwright is hosted inside the sg-send-vault-app, the vault app **proxies
`/pw/*` to this service**. Live example: `https://crisp-pascal.sg-compute.sgraph.ai/pw/`.
The service is therefore reached at a **mount prefix** (`/pw`), not at host root.

The mount prefix is resolved by `Root_Path__Resolver`
(`sg_compute_specs/playwright/core/service/Root_Path__Resolver.py:41-53`). Resolution
precedence (highest first):

| Precedence | Source | Notes |
|-----------:|--------|-------|
| 1 | `X-Forwarded-Prefix` request header | the reverse proxy already sends it (`Root_Path__Resolver.py:44-47`); the same image works behind any prefix without rebuild |
| 2 | `SG_PLAYWRIGHT__ROOT_PATH` env var | static override (`:48,:51-52`) |
| 3 | default `/pw` | `DEFAULT_ROOT_PATH = '/pw'` (`:36`) — the proxy-fronted vault-app deployment is the predominant case |

Escape hatch — **true standalone at root:** `SG_PLAYWRIGHT__ROOT_PATH=/` resolves to
`''` (no prefix) — the single `/` sentinel (`SENTINEL__NO_PREFIX`, `:38,:49-50`) is the
explicit "I am served at root" signal. All return values are normalised: no trailing
slash; `''` means no prefix (`:25`).

The same resolver feeds two consumers
(`Root_Path__Resolver.py:4-9`): the FastAPI `root_path` middleware (so `/docs` +
`/openapi.json` emit prefixed URLs) **and** `Routes__Index.index`, which templates the
prefix into `window.API_BASE`.

---

## 2. `fetch()` is already prefix-safe (`window.API_BASE`)

`Routes__Index.py` injects the resolved prefix into the page on every request:

- `Routes__Index.py:26` — `<script>window.API_BASE="__API_BASE__";</script>`
- `Routes__Index.py:613-614` — per-request,
  `INDEX_HTML.replace('__API_BASE__', Root_Path__Resolver().resolve(request))`
- `Routes__Index.py:487` — `fetch(window.API_BASE + path, ...)` — every API call is
  prefixed.

So a `fetch('/health/capabilities')` becomes `fetch('/pw/health/capabilities')` behind
the proxy and `fetch('/health/capabilities')` standalone. **The console's API calls are
already correct behind `/pw`** — this seam is unchanged by rev 3.

---

## 3. The NEW hazard — component/asset URLs (introduced by Decision #1 rev 3)

Once the console loads **served web components and asset URLs** (`sg-layout`,
`sg-tool-api`, `sg-tokens.css`, and the page's own JS), those URLs must ALSO resolve
behind the proxy. They are NOT covered by `window.API_BASE`.

**Absolute-rooted URLs break behind `/pw`.** A tag like:

```html
<link rel="stylesheet" href="/components/tokens/.../sg-tokens.css">
<script type="module" src="/api/specs/.../sg-tool-api.js"></script>
```

resolves to `host/components/...` / `host/api/specs/...` — **not**
`host/pw/components/...`. Behind the proxy these 404 (the proxy only forwards `/pw/*`).

> The admin dashboard (`sgraph_ai_service_playwright__api_site/admin/index.html`)
> mixes three URL styles — relative (`../components/...`, `:26-29`), absolute-rooted
> (`/api/specs/...`, `:37-54`), and CDN-absolute
> (`https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css`, `:7`).
> The absolute-rooted style is exactly the one that breaks behind a non-root mount
> prefix — the admin dashboard gets away with it because it is served at root. The
> sg-playwright console is predominantly served behind `/pw`, so it **must not** use
> absolute-rooted URLs.

---

## 4. The rule (Decision #11)

Every component / asset / page-JS URL the console loads must be **one of**:

- **(a) Prefix-templated** — emitted through the same resolved root_path that
  `window.API_BASE` uses. Concretely: the served `GET /` document templates the prefix
  into each component/token/JS `src`/`href` the way `Routes__Index.py:26,:613-614`
  templates `window.API_BASE`. The components are served same-origin from the existing
  static-file convention
  (`sgraph_ai_service_playwright__api_site/components/.../v0/v0.1/v0.1.0/`; precedent:
  `sg_compute__tests/control_plane/test_Spec__UI__Static__Files.py`), so a prefixed
  URL like `/pw/components/.../sg-tool-api.js` resolves through the proxy.
- **(b) CDN-absolute** — loaded from the external sgraph.ai component host
  (`https://dev.tools.sgraph.ai/...`, the same host the admin dashboard uses for
  `sg-tokens.css`). A fully-qualified `https://` URL is **prefix-independent** — it
  resolves identically behind `/pw` and at root because it does not depend on the mount
  prefix at all.

**Forbidden:** absolute-rooted URLs (`/components/...`, `/api/specs/...`) — they break
behind `/pw` (§3).

`sg-layout` and `sg-tool-api` themselves are **NOT vendored in this repo** — they come
from the external sgraph.ai component library (`dev.tools.sgraph.ai`). So choosing (a)
also implies a decision to **vendor** them under this repo's served-component path
(§5).

---

## 5. CDN vs vendored vs prefixed — the trade-off (incl. offline/egress)

| Approach | URL style | Works behind `/pw`? | Offline / locked-down deployment? | Cost |
|----------|-----------|---------------------|-----------------------------------|------|
| **CDN-absolute** | `https://dev.tools.sgraph.ai/...` (rule b) | ✅ prefix-independent | ❌ **requires browser egress to `dev.tools.sgraph.ai`** — a locked-down/air-gapped deployment cannot reach it | zero serving cost; depends on an external host + the browser's network |
| **Vendored + prefix-templated** | served from this repo's static path, URL templated like `window.API_BASE` (rule a) | ✅ via the resolved prefix | ✅ same-origin — no external egress needed | must vendor the component versions into the repo's static-file tree and keep them current |
| **Absolute-rooted** | `/components/...` | ❌ **breaks** (resolves to `host/...`, not `host/pw/...`) | n/a | forbidden |

**The offline/egress consideration is the deciding factor.** The CDN approach is the
cheapest and is prefix-independent, but it assumes the browser viewing the console can
reach `https://dev.tools.sgraph.ai`. On an offline, air-gapped, or egress-restricted
deployment (a real sg-playwright target — the service itself supports `has_network_egress`
/ `proxy_configured` capability flags), that host is unreachable and the console would
render unstyled / non-functional. For those deployments the components **must be
vendored same-origin and their URLs prefix-templated** (rule a). A robust default is to
**vendor + prefix-template** so the console is self-sufficient on every target; the CDN
form is acceptable only where browser egress to `dev.tools.sgraph.ai` is guaranteed.

> This mirrors the broader sg-playwright invariant: one Docker image must run
> identically on laptop / CI / Claude Web / Fargate / Lambda (`CLAUDE.md` Architecture).
> A console that silently depends on external CDN egress would violate that on a
> locked-down target — hence the vendored + prefix-templated default.

---

## 6. Acceptance check

> **The console works identically at `https://host/pw/` and at `https://host/`
> standalone.**

Concretely, a Dev/QA check (and the CI prefix-aware index test, brief 06 §5
`test_4__index_prefix_aware`):

1. `GET /` standalone (no `X-Forwarded-Prefix`, env unset or `=/`) → every
   component/token/page-JS URL in the returned HTML resolves to a reachable
   same-origin (or CDN) asset; `window.API_BASE` is `''`.
2. `GET /` with `X-Forwarded-Prefix: /pw` → every component/token/page-JS URL carries
   the `/pw` prefix (or is CDN-absolute and therefore unchanged); `window.API_BASE` is
   `/pw`; no absolute-rooted `/components/...` or `/api/specs/...` URL appears.
3. Loading the page behind the proxy renders the `sg-layout` shell + `sg-tool-api`
   (`window.__tool` registered), the design tokens apply, and a `fetch()` to
   `/health/capabilities` succeeds — all without any 404 on an asset URL.
4. On an egress-restricted deployment (no route to `dev.tools.sgraph.ai`), the console
   still renders because the components are vendored same-origin and prefix-templated
   (rule a), not CDN-loaded.

A failure of (2) or (4) is a **bad failure** (the console silently breaks behind the
proxy or offline) — it must be caught by the prefix-aware index check before publish.

---

## 7. Pointers

| Thing | Path |
|-------|------|
| Mount-prefix resolver (precedence) | `sg_compute_specs/playwright/core/service/Root_Path__Resolver.py:41-53` |
| `window.API_BASE` injection seam | `Routes__Index.py:26`, `:613-614`; `fetch` at `:487` |
| Admin dashboard component composition (precedent + the URL-style mix) | `sgraph_ai_service_playwright__api_site/admin/index.html:7,19,26-29,37-54` |
| Served-component static-file convention | `sgraph_ai_service_playwright__api_site/components/.../v0/v0.1/v0.1.0/`; `sg_compute__tests/control_plane/test_Spec__UI__Static__Files.py` |
| External component host (CDN) | `https://dev.tools.sgraph.ai/...` (not vendored in this repo) |
| Decision #11 + Decisions #1/#8 (rev 3) | `README.md` Locked decisions |
| Docker prefix-aware index check | `06__integration-tests.md` §5 (`test_4__index_prefix_aware`) |
