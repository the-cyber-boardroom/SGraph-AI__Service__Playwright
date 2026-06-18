---
title: "Content-transformation proxy — UX / TUI mockups"
file: 02__ux-tui-mockups.md
author: Architect (Claude)
date: 2026-06-18
version: v0.2.63
status: PROPOSED — every screen the TUI must render. Follows the Sentinel / sg_edge TUI pattern.
---

# UX / TUI mockups

The TUI is the operator surface for **development, QA, and operations**. It follows the house
pattern (verified in `…/sentinel/tui/`): **pure `*__Render` functions** + **thin Textual
screens** over a single `Content_Proxy__TUI__Source`; **every command has `--json`** and a
**no-TTY plain fallback**. Mounted as `sp content-proxy tui` (sub-screens) and as plain
sub-commands (`sp content-proxy status|traffic|scripts|transform|logs`).

Screens: 1 Dashboard/status · 2 Traffic (live flows) · 3 Flow detail · 4 Scripts (vault) ·
5 Transform (dev/QA before→after) · 6 Logs (append→S3) · 7 the CLI (non-TUI) surface.

---

## 1. Dashboard / `status`

```
┌─ content-proxy ─ status ───────────────────────────────────  stack: cp-local  [q]uit ─┐
│                                                                                        │
│  COMPONENT          PORT   AUTH        HEALTH        NOTE                               │
│  ─────────────────  ─────  ──────────  ────────────  ─────────────────────────────     │
│  mitmproxy-ext      8080   basic-auth  ● up          deliverable (a) — human browser    │
│  mitmproxy-int      8081   none        ● up          deliverable (b) — sg-playwright     │
│  mitm-service       10011  x-api-key   ● up          v0.2.1 interceptor · cookie ctrl    │
│  sg-playwright      8000   X-API-Key   ● up          chromium ready                      │
│  vault-app          443    token       ● up          4 vaults loaded                     │
│                                                                                        │
│  ACTIVE SCRIPT      scripts/transform.js  @ v0.7.3   (vault: scripts)                   │
│  FLOWS (last 5m)    142 processed · 18 injected · 3 blocked · 1 fallback                │
│  LOG VAULT          logs  →  s3://sg-cp-logs/...   (append, shared)                      │
│                                                                                        │
│  [t]raffic  [s]cripts  [x] transform  [l]ogs  [r]efresh                                 │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

No-TTY fallback (`status --json` / piped):

```
mitmproxy-ext   up   8080  basic-auth
mitmproxy-int   up   8081  none
mitm-service    up   10011 x-api-key
sg-playwright   up   8000  X-API-Key
vault-app       up   443   token
active_script   scripts/transform.js@v0.7.3
flows_5m        processed=142 injected=18 blocked=3 fallback=1
```

---

## 2. Traffic (live flows) / `traffic`

The per-request truth: was it processed, skipped (static), injected, blocked, cached, or did
the FastAPI call fall back?

```
┌─ content-proxy ─ traffic ──────────────────────────  proxy: [ext]/int   filter: [all] ─┐
│  #    TIME      VIA   METHOD  HOST / PATH                 STATUS  ACTION       FASTAPI    │
│  ───  ────────  ────  ──────  ─────────────────────────  ──────  ──────────   ────────   │
│  142  10:04:02  ext   GET     example.com/                200     injected     connected  │
│  141  10:04:02  ext   GET     example.com/app.js          200     skip(static)  —         │
│  140  10:04:01  int   GET     news.site/article/9         200     injected     connected  │
│  139  10:03:58  ext   GET     blocked.site/               403     blocked      connected  │
│  138  10:03:55  int   GET     example.com/                200     cached(req)  connected  │
│  137  10:03:50  ext   GET     slow.site/                  200     fallback     unavailable │
│                                                                                          │
│  legend: injected=script added · blocked=403 · cached(req)=answered in request phase      │
│          fallback=FastAPI unreachable (page passed through unchanged)                     │
│  [enter] flow detail   [/]filter host   [v] toggle ext/int   [p]ause                      │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

Source of truth: the `x-proxy-*` headers the interceptor stamps (`x-proxy-status`,
`x-proxy-request-count`, `x-proxy-cached-in-request`) + the TUI source tailing mitmproxy flows.

---

## 3. Flow detail (drill-in from Traffic)

```
┌─ flow #140 ─ news.site/article/9 ─────────────────────────────────────────────  [esc] ─┐
│  via mitmproxy-int   GET   200   content-type text/html   12.4 KB → 13.1 KB              │
│                                                                                          │
│  REQUEST  → POST /proxy/process-request                                                  │
│    cookies:  mitm-show=1  mitm-inject=1  mitm-debug=0                                     │
│    fastapi:  connected   modifications: headers_to_add{ x-policy: news-v3 }              │
│                                                                                          │
│  RESPONSE → POST /proxy/process-response   (body sent: 12,701 chars)                     │
│    fastapi:  connected   override_response=true                                          │
│    injected: <script src="/mitm-proxy/transform.js"></script>   (+ 41 nodes blurred)     │
│                                                                                          │
│  [b]efore/after DOM   [w] open in sg-playwright screenshot   [c] copy as curl            │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Scripts (the script vault) / `scripts`

```
┌─ content-proxy ─ scripts (vault: scripts) ─────────────────────────────────────  [esc] ─┐
│  VERSION   WHEN          ACTIVE   SIZE    NOTE                                            │
│  ───────   ───────────   ──────   ─────   ───────────────────────────────────────        │
│  v0.7.3    2026-06-17    ●  ▶     8.1 KB  add news.site selectors                         │
│  v0.7.2    2026-06-15           7.7 KB  blur PII in tables                                │
│  v0.7.1    2026-06-12           7.2 KB  initial regex-and-graph set                        │
│                                                                                          │
│  ACTIVE: v0.7.3   injected by mitm-service on every text/html response                    │
│  [enter] view source   [d] diff vs previous   [a] set active   [p] push new version       │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

> "Set active" / "push new version" are WRITE actions — gated (confirm + mutation flag),
> consistent with the spec-CLI contract and the TUI-API tier model.

---

## 5. Transform (dev / QA: before → after) / `transform <url>`

The single most useful dev/QA screen — run any URL through the live workflow and see the diff.

```
┌─ content-proxy ─ transform ────────────────────────────  url: https://news.site/9   [esc] ─┐
│  via [int]   cookies: mitm-show=1 mitm-inject=1            fastapi: connected               │
│                                                                                            │
│  ┌─ BEFORE (origin) ───────────────┐   ┌─ AFTER (transformed) ───────────────┐            │
│  │  Headline ...................... │   │  Headline ...................... │                │
│  │  Author: Jane Doe  jane@x.com    │   │  Author: Jane Doe  ████████████  │  ◀ blurred     │
│  │  Salary table:                   │   │  Salary table:                   │                │
│  │    Alice  120,000                │   │    Alice  ███████                │  ◀ blurred     │
│  │    Bob    98,000                 │   │    Bob    ██████                 │                │
│  │  [tracking pixel]                │   │  (removed)                       │  ◀ removed     │
│  └──────────────────────────────────┘   └──────────────────────────────────┘            │
│                                                                                            │
│  INJECTED: <script src="/mitm-proxy/transform.js"></script>                                │
│  RULES FIRED: blur×7  remove×2   (script v0.7.3)                                            │
│  [s] screenshot (sg-playwright)   [d] DOM diff   [j] json   [r] re-run                      │
└────────────────────────────────────────────────────────────────────────────────────────────┘
```

This drives sg-playwright (no-auth `mitmproxy-int`) under the hood — it IS deliverable (b),
surfaced for humans. `transform <url> --json` returns the structured before/after for CI.

---

## 6. Logs (append → S3 vault) / `logs`

```
┌─ content-proxy ─ logs (vault: logs, shared via S3) ─────────────────────────────  [esc] ─┐
│  source instances: cp-ec2-a, cp-ec2-b   window: [last 1h]                                 │
│  TIME      INSTANCE   VIA   EVENT          DETAIL                                          │
│  ────────  ─────────  ────  ─────────────  ───────────────────────────────────────        │
│  10:04:02  cp-ec2-a   ext   inject         example.com/  script v0.7.3                     │
│  10:03:58  cp-ec2-a   ext   block          blocked.site/  rule banned-host                 │
│  10:03:40  cp-ec2-b   int   inject         news.site/article/9                             │
│                                                                                          │
│  This vault is S3-backed — open it from any environment with the same files.               │
│  [o] reopen-vault elsewhere (prints sgit/s3 ref)   [/]filter   [f]ollow                    │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 7. The CLI surface (non-TUI; the TUI is a GUI over this)

```
sp content-proxy create  [name?] --mode direct|vault-web
                                 --vault zip:./scripts.zip --vault sgit:s3://bkt/logs
                                 --proxyauth user:pass --region --instance-type --wait
sp content-proxy list | info | delete | wait | health | connect | exec      # 8 standard verbs
sp content-proxy load-vaults [name?] --vault ...                            # the deploy copy-in
sp content-proxy status   [name?] [--json]
sp content-proxy traffic  [name?] [--via ext|int] [--json] [--follow]
sp content-proxy scripts  [name?] [--json]            # list/diff/set-active/push
sp content-proxy transform <url>  [--via int|ext] [--cookie mitm-show=1] [--json]
sp content-proxy logs     [name?] [--json] [--follow]
sp content-proxy tui      [name?]                     # the Textual app (all screens above)
```

Every command: `--json` for machines + a plain no-TTY fallback (Sentinel rule). The TUI owns
**no logic** — it renders what the CLI/source returns (`v0.2.39__tui_cli_separation.md`).

---

## 8. Render/screen split (so tests are trivial — see doc 05)

```
  Content_Proxy__TUI__Source        # data only: polls status, tails flows, reads vaults
        │  returns Type_Safe schemas
        ▼
  *__Render functions (pure)         # schema → Rich renderable / plain string ; unit-tested
        │
        ▼
  Textual Screen classes (thin)      # wire keys → source → render ; smoke-tested headless
```

Mirror `…/sentinel/tui/{source,screens}` + `…/sentinel/tui/screens/test_renders.py`.
</content>
