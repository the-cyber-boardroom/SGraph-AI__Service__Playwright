---
title: "Review — v0.2.64 console effort on the sg-playwright image, + cookie-injection analysis"
file: review__v0.2.64-console-and-cookie-question.md
author: Claude (Fable — reviewer role)
date: 2026-07-03
repo: "SGraph-AI__Service__Playwright @ claude/amazing-pasteur-3srh6x (HEAD b539e2c at review time)"
status: REVIEW — findings + recommendations; cookie section is PROPOSED design, does not exist yet
audience: Dinis
---

# Review — the v0.2.64 console effort, and "how do we set a cookie on a site?"

## 1. Scope and commit ledger

Ten commits on `claude/amazing-pasteur-3srh6x` since the dev merge-base, reviewed against the
code, tests, and docs as of `b539e2c`:

| Commit | What |
|---|---|
| `9fe5917` | P1 — auth-aware health bootstrap, XSS escape, guards, prefix-aware docs link |
| `f4c84ec` | P2–P5 — rebuild `GET /` into the capability-driven, agent-native console (8 tabs, 24-verb builder, workflows, in-app docs, `window.__tool`) |
| `01a0740` | P6–P7 — integration tests + `integration-test-image` CI gate; debrief; reality-doc D1 fix (16→21 endpoints) |
| `609a495` | Merge `origin/dev` (deps caps, `routes_paths_all()` test fix, content-proxy fixes, v0.2.64 bump) |
| `c27b8da` | Iteration 2 — light work panes, first sg-layout attempt, framed screenshot viewer, `copyText` clipboard fix, `/test-pages/*` + S1–S5, D7/W2 fix, `__tool` REPL |
| `9b2b24c` | sg-layout attempt #2 (id-based slot projection) — still wrong, but added the verify-or-revert guard |
| `d3d8867` | Drop sg-layout; in-house splitter grid; fix `applyCapabilities` null crash |
| `512da60` | Bring sg-layout back the documented way (tag-hosted `sg-pane-*` elements) — **works** |
| `d562403` | Render inline per-step screenshots (artefact-type case bug); collapsible step cards |
| `b539e2c` | Output gets its own pane; `revealOutput()` on execute; layout key → v3 |

Verification state: 110 route-level tests green in `.venv312`; JS validated with `node --check`
throughout; the operator confirmed the live console working via screenshots (light theme,
sg-layout panels with tabs/drag/resize, framed screenshot viewer, gallery). The
Chromium-gated integration tier (`tests/integration/`, UI-execute smoke) has still never run
in-session — it runs in the `integration-test-image` CI job.

## 2. What the image now ships (net effect)

- **`GET /` console** — capability-driven (UI gates on live `/health/capabilities`), 8 endpoint-family
  tabs, 24-verb sequence builder with collapsible step cards, workflow save/load/export/import,
  S1–S5 self-contained examples + W1–W9, in-app docs generated from the live capability surface,
  agentic `window.__tool` + bottom REPL, sg-layout panel shell (Builder | Output over Examples,
  Console dock) with plain-grid fallback, light work panes / dark chrome, prefix-aware behind `/pw`.
- **`GET /test-pages/{simple,form,dynamic,links,slow}`** — deterministic fixtures served by the
  service, auth-excluded so the server-side browser reaches them keyless. Route count 21 → 22.
- **CI** — `integration-test-image` now runs `test_99_ui_console.py` (console + capabilities +
  `/pw` prefix checks against the built image) before `push-playwright-manifest` publishes.

## 3. Findings

Severity: 🔴 needs fixing · 🟡 should fix / decide · 🔵 note for the record.

### F1 🔴 `chromium 0.0.0 · degraded` health badge (server-side, pre-existing, still open)
Screenshots render fine, yet `/health` reports `chromium 0.0.0` and the console badge shows
*degraded* on every deployment we've seen (laptop + docker). Almost certainly the version probe
in the health/capability detector, not the browser. It poisons the one signal the console
header exists to give. **Recommend: next slice, small.** (Flagged in three prior turns; never
picked up.)

### F2 🟡 `.claude/CLAUDE.md` architecture section is stale
Still says "**16 direct endpoints** … Routes__Session removed in v0.1.24" and "**12 service
classes**". Reality (and the reality doc + catalogue, both corrected this session) is **22**
route families with `Routes__Session` and `Routes__Inspect` wired
(`Fast_API__Playwright__Service.py:106-115`). Every agent reads CLAUDE.md first; it currently
contradicts the canonical reality doc. Deliberately left to the human per the slice constraint —
but it has now survived three slices. **Recommend: one-line fix, human-approved, this week.**

### F3 🟡 Reality doc + debrief drifted behind the last five commits — **fixed in this commit**
`9b2b24c`→`b539e2c` changed only code + tests. The reality doc still described the *first*
(broken) sg-layout wiring (`layout:v1` key, 3 panes, slot-projection); the debrief stopped at
iteration 2. That violates CLAUDE.md rule "update the reality document when you change code".
Corrected now: reality-doc `GET /` row rewritten (4 tag-hosted panes, `layout:v3`,
`tools.sgraph.ai` host, Output pane, collapsible cards, artefact-case fix); debrief §9 addendum
covers iterations 3–5.

### F4 🟡 The sg-layout episode — process lesson worth institutionalising
Two integrations shipped on guessed contracts (slot-projection, then id-based projection) and
broke the page for the operator both times; the correct pattern (`tag`-instantiated hosts) was
obvious the moment the real docs (`v0.1.92__sglayout__quickstart/full-inventory`) arrived.
Classification per §27: **bad failure** (shipped unverifiable, twice), converted to good by the
docs. Two durable fixes:
1. **Mirror the two sg-layout guidance docs into `library/guides/`** (they arrived as chat
   uploads; nothing in-repo prevents the next agent repeating the guess cycle). Also fix the
   stale header comment in `Routes__Index.py` (~line 24) that still narrates the old 404/CDN
   story.
2. **A JS-executing render smoke in CI** — the existing image gate checks `GET /` returns the
   HTML but never *runs* it; an empty-shell regression would pass today's gate. One
   Chromium-gated assertion ("builder pane has a non-zero box after load") in
   `test_99_ui_console.py` closes that hole.

### F5 🔵 `/test-pages/{unknown}` returns 401 (not the escaped 404) when an API key is set
The auth-exclude list enumerates the five names, so unknown names hit the key middleware first.
Cosmetic; the S-series only uses known names. Fix only if it bites.

### F6 🟡 W1, W6, W7, W9 gallery examples still target external / fictional URLs
(`example.com/catalog`, `app.example.com`…) — they 4xx or hang on egress-restricted deployments,
which is exactly the trap the S-series was built to avoid (the operator hit it with W1 before
the fixtures existed). **Recommend:** either retarget them at `/test-pages/*` variants or badge
them "needs egress" in the gallery so the failure is expected rather than mysterious.

### F7 🔵 Local venv vs merged dependency caps
`origin/dev` capped `fastapi <0.131` / `starlette <1.0`; `.venv312` still runs 0.138/1.3.1.
Tests pass because dev also rewrote the route-scan tests, but local green ≠ pinned-stack green.
Reinstall the venv before trusting dependency-sensitive results locally. CI installs fresh, so
the image is unaffected.

### F8 🔵 Publish flow for EC2
`sp docker create` pulls the *published* Docker Hub tag; this branch's console reaches EC2 only
after merge → CI gate → `push-playwright-manifest`. `version` is now v0.2.64 via the dev merge,
so the tag story is clean.

## 4. Recommended order of work

1. **F1** health badge / chromium-version probe (small, user-visible, longest-open).
2. **F2** CLAUDE.md endpoint line (one line, needs your sign-off).
3. **F4.1** mirror sg-layout docs into `library/guides/` + fix the stale `Routes__Index.py` header note.
4. **F6** retarget or badge the egress-dependent W-examples.
5. **F4.2** JS-executing console smoke in the CI image gate.
6. **Cookie verb** (below) — natural next feature slice; pairs with a `/test-pages/cookies` fixture.

---

## 5. "How can we set a cookie on a particular site?" (open page → set cookie → reload → screenshot)

### What exists today (reality-doc-grounded)

| Mechanism | Where | Scope & limits |
|---|---|---|
| `credentials.cookies_vault_ref` | `Schema__Sequence__Request.credentials` (also `/inspect`, sessions) → `Credentials__Loader.apply()` → `context.add_cookies()` | Real jar cookies, applied to the fresh context **before step 1** (Sequence__Runner step 7). Requires the cookie JSON to already live in the vault (`has_vault_access`). Cannot change cookies mid-sequence. |
| `credentials.extra_http_headers` | Same schema, **inline** (no vault) | Can carry `Cookie: name=value` today, zero code change. But it's a *request header*, not a jar cookie: sent on every request in the context, invisible to `document.cookie`, no domain/path/expiry semantics. Fine when the target *server* reads the cookie; wrong for a JS-visible demo. |
| `evaluate` step with `document.cookie='…'` | `/sequence/execute` | Blocked in practice: `JS__Expression__Allowlist` is deny-all by default (rule 10), and it could never set `HttpOnly` cookies anyway. Not a path. |
| `/auth/set-cookie-form` (`Routes__Set_Cookie`) | Service API surface | **Name collision, different feature** — sets the service's *own* API-key cookie so a human browser can authenticate to the service. Nothing to do with target-site cookies. |

So: the exact flow you describe — *open page, set cookie, reload, screenshot showing the
cookie in action* — **is not expressible today**. Cookies can only enter at context creation,
and only from the vault.

### PROPOSED — `set_cookie` step verb *(does not exist yet)*

The 24-verb dispatcher is the right seam; this is a textbook small slice:

1. **`Enum__Step__Action.SET_COOKIE = "set_cookie"`** (+ optionally `GET_COOKIES = "get_cookies"`
   as a Φ3-style read verb, so sequences can *assert* the jar).
2. **`Schema__Step__Set_Cookie`** (own file, pure data): `name`, `value`, `url` *or*
   `domain` + `path` (Playwright's `add_cookies` contract), `secure : bool`,
   `http_only : bool`, `same_site : Enum__Cookie__Same_Site {strict, lax, none}` (rule 3 — no
   Literals), optional `expires` timestamp. Register in `STEP_SCHEMAS`.
3. **Execution boundary** — keep the single-owner rule intact: `Credentials__Loader` is already
   the only class allowed to call `context.add_cookies` (its header says so). Add
   `Credentials__Loader.add_cookie(context, schema)`; `Step__Executor` dispatches the verb and
   passes `page.context`. No new `page.*` surface, rule 16 untouched.
4. **Sequence semantics** — "reload" is simply a second `navigate` to the same URL (fresh
   request carries the new jar). No `reload` verb needed; document the pattern.
5. **Console/docs propagate automatically-ish** — the in-app docs and `__tool` API skill
   generate from the `VERBS` surface, and `test_Routes__Index__verb_table_drift.py` will *fail*
   until the console's hand-mirrored `VERBS` table gains the new verb — the drift guard doing
   its job.
6. **New fixture: `/test-pages/cookies`** — client-side JS renders `document.cookie` into a
   stable `#cookie-list`, with `#no-cookies` / `#has-cookies` banners. Then a new self-contained
   gallery example (S6):
   `navigate(/test-pages/cookies)` → `screenshot` (shows *no cookies*) →
   `set_cookie{name:'sg_demo', value:'hello', url:<origin>}` → `navigate` again →
   `screenshot` (banner + value visible). Deterministic, keyless, works on every deployment.
   *(Demo cookie must not be `HttpOnly`, or `document.cookie` won't show it.)*

**Security notes to bake in:** inline cookie values are secrets-in-request-body — fine for test
cookies, wrong for real session tokens (the vault path stays the production route). Redact
`value` in echoed step results, and extend the console's "Copy as curl" placeholdering (it
already placeholders the API key) to cookie values.

**Effort:** enum + schema + loader method + executor dispatch + registry + fixture page + S6 +
body-level tests + one gated live test + capability-map/reality-doc rows. Comparable to the
Φ4 read-verbs slice.

### If you want the demo *today*, before the verb exists
`POST /sequence/execute` with
`credentials: { extra_http_headers: { "Cookie": "sg_demo=hello" } }` + navigate + screenshot —
works unchanged on `/inspect` too. Honest caveat: header-level, so the fixture page above
(which reads `document.cookie`) would show nothing; it only demonstrates cookies the *server*
reacts to. The verb is the real answer.
