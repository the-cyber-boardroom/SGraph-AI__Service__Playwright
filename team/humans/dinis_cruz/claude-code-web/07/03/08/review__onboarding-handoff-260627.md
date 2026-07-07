---
title: "Review — response to the onboarding-pipeline sg-playwright handoff (2026-06-27)"
file: review__onboarding-handoff-260627.md
author: Claude (Fable — reviewer role)
date: 2026-07-03
repo: "SGraph-AI__Service__Playwright @ claude/amazing-pasteur-3srh6x (HEAD 6eb08da at review time)"
status: REVIEW — code-grounded answers to the handoff's 9 questions; proposals labelled PROPOSED
source_doc: "sg_playwright_api_findings_handoff_260627_1.md (Akeia onboarding team)"
audience: Dinis
---

# Review — the onboarding-pipeline handoff, answered against the code

The handoff is a good, careful field report. Several of its blockers are now smaller than it
thought, one is already **fixed this session**, and one central assumption (a "~950 node cap")
is a **misdiagnosis**. Answers below are grounded in the actual code, not the OpenAPI surface,
with `file:line` cites. Every "PROPOSED" item does not exist yet.

## TL;DR for the pipeline team

- **Cookies (their Q8/Q9, P2): mostly solved as of today.** The new `set_cookie` step verb sets a
  cookie on the per-request browser context before navigation, statelessly. Their exact
  "inject → reload → screenshot" flow is now one `/sequence/execute` body. Detail in Q8.
- **Node budget (their P0): there is no node cap.** Nothing in the service caps node count; the
  only limiter is `max_depth` (default 8) plus visible-only filtering. Raising `max_depth` and
  scoping with `root_selector` is the lever today; a `skip_selectors` param is the right small add.
- **`root_selector` (their P0): real, intentional, honoured** for `get_dom_tree`. It's a
  Type_Safe schema field, so it is already in the generated `openapi.json`. (Not yet honoured for
  `get_a11y_tree` — a real gap.)
- **Scripts / `evaluate` (their P1): the blocker is that there is NO boot-time wiring to open the
  allowlist.** The class comment claims "populated at boot from vault config" but no code does
  that. Enabling scripts is a small *build*, not a config flag that exists today — and it's
  security-gated (CLAUDE.md rule 11), so the shape is Dinis's call. See Q4 + the separate
  "script capability" note.
- **Health badge** they'd have seen (`degraded · chromium 0.0.0`) was a **service bug, fixed this
  session** — unrelated to their pipeline but it would have made every probe look unhealthy.

## Answers to the 9 questions

### Q1 — Node budget (~950 cap). *There is no cap.*
`DOM_TREE_JS` (`Step__Executor.py:511-573`) recurses purely by `maxDepth` and skips invisible
nodes unless `include_invisible`; there is **no node counter, no `maxNodes`, no truncation**. The
result field is a plain `Dict` (`schemas/results/Schema__Step__Result__Base.py:54`) — not a
size-capped `Safe_Str` — so the payload isn't clipped either. The "945 nodes at depth 9 → cap"
they saw is simply how many visible nodes exist within depth 9 of `<body>`; deeper card
internals are cut by `max_depth`, not a budget.
- **`max_depth` is an unbounded `Safe_UInt`** (`schemas/steps/Schema__Step__Get_Dom_Tree.py:23`,
  default 8) — callers can already raise it. The practical limiter is payload size / model
  tokens, which their own doc says is fine (~3k nodes ≈ 100k tokens).
- **PROPOSED (P1):** add an explicit `max_nodes` *safety* cap (opt-in, high default) so large
  pages fail predictably instead of returning a multi-MB tree, **and** a `skip_selectors:[…]`
  param (see Q3). The honest framing to the team: stop thinking "raise the cap" — there's no
  cap; think "spend depth wisely" (root_selector + skip_selectors + higher max_depth).

### Q2 — `root_selector`: supported and intentional.
Honoured in `execute_get_dom_tree` (`Step__Executor.py:394-397`, passed as `rootSelector` into
the JS). It's a first-class `Safe_Str__Selector` schema field, so it **already appears in
`/openapi.json`** — if the team can't see it via `/pw/openapi.json`, check whether the content
proxy is serving a stale/cached spec, not the service.
- **Gap:** `get_a11y_tree` explicitly does **not** honour `root_selector` yet
  (`Step__Executor.py:423-425` — CDP `queryAXTree`/backendNodeId work deferred). Their strategy of
  "a11y tree for headline text" returns the whole-document tree today.
- **PROPOSED (P0, cheap):** document `root_selector` fallback semantics in the schema description;
  honour it for `get_a11y_tree`.

### Q3 — Traversal order + `skip_selectors`. *Depth-first; no skip today.*
`nodeData` recurses first-child-first (`Step__Executor.py:541-570`) — depth-first, confirmed. No
`skip_selectors`. Breadth-first would help their "header/nav eats the budget" complaint, but with
no node cap the real win is **`skip_selectors`** (drop `header,nav,footer,aside` subtrees so
depth is spent on content). It's ~5 lines in `DOM_TREE_JS` (skip if `el.matches(skipSel)`), cheap
and auditable. **PROPOSED (P1):** `skip_selectors : List[Safe_Str__Selector]` on
`Schema__Step__Get_Dom_Tree`. Prefer this over BFS (smaller change, more predictable output).

### Q4 — `evaluate` allowlist. *Deny-all, and not wired to any boot config.*
`JS__Expression__Allowlist` starts empty with `allow_all=False`
(`service/JS__Expression__Allowlist.py`). The main sequence/inspect runner constructs its
validator with the default (deny-all) allowlist; **nothing reads an env var or vault to populate
`allowed_expressions` or flip `allow_all`** — I grepped the whole core. The class docstring's
"populated at boot time (typically from a vault-stored config)" is **aspirational, not
implemented.** The only `allow_all=True` path is the dedicated screenshot runner
(`Playwright__Service.py:104`).
- So their ask "can expressions be added on this instance / `allow_all` for a dedicated EC2" has
  **no mechanism today** — it needs a small feature (env/vault → allowlist). This is the crux of
  the "script capability" request; treated separately below because it's security-gated
  (CLAUDE.md rules 10–11) and the *shape* is a deliberate posture decision.
- **Important reframe for the team:** most of their *recon* (`get_dom_tree`, `get_a11y_tree`,
  `get_text`, `get_html`, `get_console_tail`, `get_network_failures`) needs **no `evaluate`** —
  those verbs run built-in introspection JS that bypasses the allowlist by design
  (`Step__Executor.py:397` comment). `evaluate` is only needed for their `FilterDebug(80)` and
  the mutation counter. See Q6 for a cheaper path to those.

### Q5 — Inline screenshot returns 7 bytes through `/pw/`. *Almost certainly the proxy, not the service.*
The service returns `screenshot_b64` inline correctly on direct access (we exercised it live this
session — multi-hundred-KB PNGs render in the console). `Schema__Screenshot__Response` carries
`screenshot_b64` as a full base64 string with no cap. A 7-byte body is the signature of a
**content-proxy response-body rewrite/limit on the `/pw` path**, not sg-playwright.
- **Recommend:** hit `/screenshot` on the instance directly (bypassing `/pw`) to confirm; if it's
  full there, the bug is in the content_proxy layer (Caddy/mitm response handling), which is a
  different repo. Flag to whoever owns the content_proxy AMI.

### Q6 — Screenshot `return_value`. *Confirmed discarded — and worth adding.*
`Schema__Screenshot__Response` is exactly `{url, screenshot_b64, html, duration_ms, trace_id}`
(`schemas/screenshot/Schema__Screenshot__Response.py:14-18`) — **no `return_value` field**, so the
JS result is dropped even though the screenshot runner runs it with `allow_all`. (The "html ~4
chars" they saw is `null` serialised — for `format=png`, `html` is None.)
- **PROPOSED (P2, clean win):** add `return_value : Dict = None` to the screenshot response and
  populate it from the `javascript` expression. This gives them `evaluate`-equivalent reads
  (mutation count, `FilterDebug` JSON) **without** touching the gated sequence/inspect allowlist —
  the screenshot runner is already `allow_all` and each call is an isolated ephemeral session.
  This is the single highest-leverage, lowest-risk item in their whole list.

### Q7 — Xvfb / stealth on the AMI.
`Browser__Launcher.DEFAULT_LAUNCH_ARGS` = `--no-sandbox --disable-gpu --disable-dev-shm-usage
--single-process --use-mock-keychain` (`service/Browser__Launcher.py`). **No stealth args**, and
no explicit `--enable-automation` (Playwright adds that itself by default). `headless` comes from
`browser_config`; the service faithfully passes `headless:false` but the AMI has no display →
their `Missing X server` error.
- Two independent asks: **(a) Xvfb in the image** (headed mode), **(b) stealth args** (evade
  Akamai). Both are image/launch changes, not schema changes. `--single-process` may fight some
  stealth setups — worth testing.
- **PROPOSED (internal-image only, P1):** an opt-in launch profile — env-gated stealth args
  (`--disable-blink-features=AutomationControlled`, `ignoreDefaultArgs=['--enable-automation']`,
  a `navigator.webdriver` init script) + Xvfb in a dedicated internal image. Keep the
  customer-facing image headless/plain. This aligns with their internal-vs-customer split (§119).

### Q8 — Cookie before navigation (pipeline). *Solved today.*
The new **`set_cookie` step verb** (shipped this session, `Enum__Step__Action.SET_COOKIE`,
`Schema__Step__Set_Cookie`) sets a cookie on the per-request context **before** the next
navigate, statelessly (fresh context per request, discarded after). Their Flow-B
"inject → screenshot with filter running" becomes one `/sequence/execute` body:
```
steps:
  - {action: set_cookie, name: "mitm-mode", value: "inject", url: "https://target.example"}
  - {action: navigate,   url: "https://target.example"}
  - {action: screenshot, full_page: true}
capture_config: {screenshot: {enabled: true, sink: inline}}
```
Cookie-gated / opt-in injection is preserved (only requests that carry the step get the cookie —
no always-on injection, so unfiltered browsing and cost control are intact, exactly their
requirement §193). Vault-sourced cookies (`credentials.cookies_vault_ref`) and inline auth
headers (`credentials.extra_http_headers`) also already existed for the pre-context path.
- **Caveat to pass on:** a `HttpOnly` cookie won't be visible to page JS; for a MITM signal
  cookie that's fine (the proxy reads the request header). Real session cookies belong in the
  vault path, not inline.

### Q9 — Cookie injection *through `/pw/`* for filtered screenshots.
This is the proxy-path variant of Q8. `set_cookie` works on `/sequence/execute` regardless of
whether the call arrives via `/pw` — **provided the content proxy forwards the request body
untouched** (it should; it's a POST body, not a header the proxy strips). The open question is
purely whether the `/pw` content proxy interferes, same layer as Q5. Recommend testing
`set_cookie` end-to-end through `/pw` on the live instance; if the body survives, Q9 is closed by
Q8.

## Cross-cutting: mutation observation (their P3)
No native "observe mutations for N seconds" verb exists; today it requires `evaluate` +
`MutationObserver`. **PROPOSED (P3):** a `wait_for_mutations`/`observe_mutations` verb that
installs a `MutationObserver` server-side for a bounded window and returns a change summary —
built-in JS, so it needs no allowlist opening, unlike their current `evaluate` route. This would
let onboarding classify "static-after-load vs continuous-churn" without opening scripts at all.

## Recommended priority (reconciling their table with the code)

| Pri | Item | Note |
|---|---|---|
| **Done** | Cookie-before-navigate | `set_cookie` verb shipped (Q8). Test through `/pw` (Q9/Q5 proxy). |
| **P0** | Document `root_selector`; honour it for `get_a11y_tree` | Already works for dom_tree; a11y is the gap (Q2). |
| **P0** | Correct the "node cap" narrative + add `skip_selectors` | There is no cap; skip_selectors > raising a phantom max_nodes (Q1/Q3). |
| **P1** | Screenshot `return_value` | Highest-leverage, lowest-risk; evaluate-equivalent reads with no allowlist change (Q6). |
| **P1** | Script-capability boot wiring (env/vault → allowlist) | Needs a build + a posture decision; see the separate note. Security-gated (Q4). |
| **P1** | Internal stealth+Xvfb image profile | Image change, opt-in, internal-only (Q7). |
| **P2** | `max_nodes` explicit safety cap | Predictable failure on huge pages (Q1). |
| **P3** | Native `observe_mutations` verb | Removes their last `evaluate` dependency (P3). |
| **proxy** | 7-byte inline screenshot; `/pw` body passthrough | Content-proxy layer, different repo (Q5/Q9). |

## What I've already fixed this session (context for the team)
- `set_cookie` verb + `/test-pages/cookies` fixture + an S6 console example demonstrating exactly
  their inject→reload→screenshot flow.
- Health badge: `/health/status` no longer reports `degraded` just because the vault env is
  absent (connectivity is now a non-gating check), and `chromium_version` reports the real version
  (`148.0.7778.96`) instead of `0.0.0`.
