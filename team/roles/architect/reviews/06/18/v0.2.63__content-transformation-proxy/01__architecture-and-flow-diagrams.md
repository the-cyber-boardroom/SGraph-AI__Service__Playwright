---
title: "Content-transformation proxy — Architecture & flow diagrams (ASCII)"
file: 01__architecture-and-flow-diagrams.md
author: Architect (Claude)
date: 2026-06-18
version: v0.2.63
status: PROPOSED — the mental model. Every topology + flow in ASCII.
---

# Architecture & flow diagrams

All diagrams are ASCII so they render identically everywhere. Index:

1. The big picture (one instance, two mitmproxies)
2. Mode 1 — human browser through the authed proxy
3. Mode 2 — sg-playwright through the no-auth proxy (the QA path)
4. The interceptor ↔ FastAPI request flow
5. The interceptor ↔ FastAPI response flow (where the script is injected)
6. The injected script — client-side transform
7. The vault's three roles (data movement)
8. Vault loading at build/deploy (zip / sgit)
9. Scaling — ASG + the two load balancers
10. Component / port map
11. Local vs EC2 targets
12. The `/mitm-proxy` smoke check (MVP) + the `/pw` on `:443` path
13. TLS termination (Let's Encrypt / ACM)

---

## 1. The big picture — one instance, two mitmproxies, one workflow

```
                         ┌──────────────────────  ONE INSTANCE (docker-compose)  ──────────────────────┐
                         │                                                                              │
  Human browser          │   ┌──────────────────────┐                                                  │
  (proxy configured) ════╪══▶│ mitmproxy-ext  :8080  │══╗   (basic auth)                                │
        MODE 1           │   │ stock img + addon     │  ║                                               │
                         │   └──────────────────────┘  ║                                               │
                         │                              ║   POST /proxy/process-request                 │
                         │                              ╠══▶ POST /proxy/process-response ┌───────────┐ │
                         │   ┌──────────────────────┐  ║      (HTML body + Cookie)        │  FastAPI  │ │
  sg-playwright  :8000 ──╪──▶│ mitmproxy-int  :8081  │══╝                                  │   MITM    │ │
   (scripted browser)    │   │ stock img + addon     │       returns: modified_body =      │  service  │ │
        MODE B / QA      │   │ NO auth (net-local)   │       page + injected <script>      │  :10011   │ │
                         │   └──────────────────────┘                                      └─────┬─────┘ │
                         │                                                                       │ reads │
                         │   ┌──────────────────────┐         /pw reverse-proxy            ┌─────┴─────┐ │
                         │   │  vault app  :443      │◀────────  (browser → playwright) ────│  script   │ │
                         │   │  SG API + vault + UI  │                                      │  vault    │ │
                         │   └──────────┬───────────┘                                      └───────────┘ │
                         └──────────────┼───────────────────────────────────────────────────────────────┘
                                        │ append logs / read-write vaults
                                        ▼
                                   S3  (shared vault store — whole fleet feeds this)
```

Both mitmproxies run the **same** interceptor and hit the **same** FastAPI workflow. The only
difference is `--proxyauth` on the external one.

---

## 2. Mode 1 — human browser through the authed proxy (deliverable a)

```
  ┌────────────┐  proxy: http://USER:PASS@<lb>:8080   ┌──────────────┐  fetch   ┌─────────┐
  │  Human     │ ───────────────────────────────────▶ │ mitmproxy-ext │ ───────▶ │ Origin  │
  │  browser   │ ◀─────────  transformed page  ─────── │  (basic auth) │ ◀─────── │ website │
  └────────────┘                                       └──────┬───────┘          └─────────┘
                                                              │ HTML → FastAPI → modified_body
                                                              ▼
                                                     ┌──────────────────┐
                                                     │ FastAPI MITM svc  │  inject <script>
                                                     └──────────────────┘
```

The browser must trust the mitmproxy CA (install the CA, or accept the warning). Basic-auth
creds are the proxy credentials the user configures.

---

## 3. Mode B — sg-playwright through the no-auth proxy (deliverable b, the QA path)

```
  ┌────────────────┐  HTTP API (X-API-Key)   ┌──────────────┐
  │  test / agent  │ ──────────────────────▶ │ sg-playwright │   browser launched with
  │  (pytest, CLI) │   /sequence/execute      │   :8000      │   proxy=http://mitmproxy-int:8081
  └────────────────┘                          └──────┬───────┘   IGNORE_HTTPS_ERRORS=true
                                                     │ browser traffic
                                                     ▼
                                              ┌──────────────┐  fetch   ┌─────────┐
                                              │ mitmproxy-int │ ───────▶ │ Origin  │
                                              │  (NO auth)    │ ◀─────── └─────────┘
                                              └──────┬───────┘
                                                     │ HTML → FastAPI → modified_body
                                                     ▼
                                              ┌──────────────────┐
                                              │ FastAPI MITM svc  │  (SAME workflow as Mode 1)
                                              └──────────────────┘

  QA asserts: the DOM the browser rendered has the policy transform applied
              (extract text / DOM / screenshot, compare to expectation).
  Cookies:    the sequence sets mitm-* cookies on the context to drive activation.
```

No `--proxyauth` here — that is the whole point. Playwright drives a clean proxy.

---

## 4. Interceptor ↔ FastAPI — request flow

```
  request(flow)                                         FastAPI  POST /proxy/process-request
  ────────────                                          ─────────────────────────────────────
  should_process_request(flow)?
    • method != GET                  → skip
    • path starts /mitm-proxy        → ALWAYS process (admin/static for the MITM UI)
    • static ext (.js/.css/.png/...) → skip
    • else                           → process
        │
        ▼ POST { method, host, path, headers(incl Cookie), stats, version }
        │ ◀── modifications:
        │       cached_response? {status, body, headers}  → short-circuit, serve now
        │       block_request?   {status, message}        → 403 response, stop
        │       headers_to_add / headers_to_remove        → mutate request
        ▼
  forward to origin (or served/blocked above)
```

`cached_response` lets the **request** phase fully answer (no origin fetch) — marked
`x-proxy-cached-in-request: true` so the response phase skips it.

---

## 5. Interceptor ↔ FastAPI — response flow (the injection point)

```
  response(flow)                                        FastAPI  POST /proxy/process-response
  ─────────────                                         ──────────────────────────────────────
  should_process_response(flow)?
    • cached-in-request → skip
    • content-type not text/html → skip          (images/json/etc. pass untouched)
    • else → process
        │
        ▼ POST { request{...,headers incl Cookie}, response{status, headers, content_type,
        │        body(=full HTML)}, stats, version }
        │ ◀── modifications:
        │       override_response? {status, content_type, modified_body}
        │       modified_body  → flow.response.content = page + injected <script>   ◀── THE INJECT
        │       headers_to_add / headers_to_remove
        │       include_stats  → x-proxy-stats header
        ▼
  deliver transformed page to the browser
```

The FastAPI service is where the cookie decision + the `<script>` injection happen. The
interceptor is dumb plumbing: capture → POST → apply.

---

## 6. The injected script — client-side transform

```
  Browser receives:  <html> ... origin content ...
                     <script src="/mitm-proxy/transform.js"></script>   ◀── injected by FastAPI
                                   │
                                   ▼  runs BEFORE the user reads the page
                     ┌─────────────────────────────────────────────┐
                     │ transform.js (the "formula")                 │
                     │  • regex-and-graph rules (today)             │
                     │  • blur  matched nodes                       │
                     │  • remove matched nodes                      │
                     │  • (future) semantic-graph, dynamic          │
                     └─────────────────────────────────────────────┘
                                   │
                                   ▼
                     User sees only policy-allowed content
```

The script is the unit of policy; it is versioned in the **script vault** and the MITM service
serves/injects the latest.

---

## 7. The vault's three roles (data movement)

```
   ROLE 1  SCRIPTS IN                 ROLE 2  LOGS OUT (append → S3)        ROLE 3  VAULT APPS
   ─────────────────                  ───────────────────────────          ──────────────────
   script vault ──▶ MITM service      EC2 #1 ─┐                             UX launcher  ─┐
   (versioned)      injects latest    EC2 #2 ─┼─append─▶ log vault ─▶ S3    testing tools ─┼─▶ user
                                      EC2 #N ─┘             ▲                              ─┘
   update filtering                   reopen the SAME       │  same S3 files
   = update the vault                 vault from anywhere ──┘  (fleet = one vault)
```

---

## 8. Vault loading at build / deploy

```
  Create stack
       │
       ▼  docker-compose up   (the 5 services)
       │
       ▼  load-vaults  ──┬── kind=ZIP  : copy bundled archive → vault app
                         └── kind=SGIT : sgit clone <ref from live server | s3://bucket> → vault app
       │
       ▼  vaults present:  [ scripts ]  [ logs(append target) ]  [ ux-launcher ]  [ testing ]
       │
       ▼  ready
```

`Schema__Content_Proxy__Vault__Source { kind: ZIP|SGIT, ref, target }`. Precedent for the sgit
path in user-data: `Section__SGit_Venv.py`.

---

## 9. Scaling — ASG + two load balancers (per mode)

```
   MODE 1 (direct proxy, L4)            MODE 2 (vault/web, L7)
   ┌───────────────────────┐           ┌───────────────────────────┐
   │  Network Load Balancer │           │ Application Load Balancer  │
   └───────────┬───────────┘           └─────────────┬─────────────┘
               │                                      │
        ┌──────┴───────────────  Auto Scaling Group  ─┴──────┐
        ▼                         ▼                          ▼
   [ instance 1 ]           [ instance 2 ]     ...      [ instance N ]
        └──────────────────────────┬──────────────────────────┘
                                    ▼  all feed
                              S3 (shared vaults)
```

NLB for the raw proxy port (L4, CONNECT/tunnels); ALB for vault/web (L7). No instance holds
unique state, so the group scales freely.

---

## 10. Component / port map

```
  ┌────────────────┬───────┬─────────────┬───────────────────────────────────────────┐
  │ Service        │ Port  │ Auth        │ Reached by                                  │
  ├────────────────┼───────┼─────────────┼───────────────────────────────────────────┤
  │ mitmproxy-ext  │ 8080  │ basic auth  │ human browser (via NLB)         [deliv. a]  │
  │ mitmproxy-int  │ 8081  │ none        │ sg-playwright browser (net only)[deliv. b]  │
  │ mitm-service   │ 10011 │ x-api-key   │ both interceptors (net only)                │
  │ sg-playwright  │ 8000  │ X-API-Key   │ net-only; browsers reach it via vault /pw:443│
  │ vault-app      │ 443   │ token/TLS   │ users (via ALB); /pw → sg-playwright; UX     │
  └────────────────┴───────┴─────────────┴───────────────────────────────────────────┘
  Images (Docker Hub): mitmproxy/mitmproxy (stock) · diniscruz/sg-playwright · diniscruz/sg-send-vault
                       + the MGraph-AI MITM service image (ref TBD).
  Network-local only (never in the SG / LB): 8081, 10011, 8000.
  Externally exposed: 8080 (NLB, mode 1) and 443 (ALB, mode 2, TLS).
  KEY: sg-playwright :8000 is NOT browser-reachable — a :443 vault page reaches it ONLY
       same-origin via https://<host>/pw/* (the v0.2.41 reverse-proxy seam).
```

---

## 11. Local vs EC2 targets (mirror the Sentinel multi-target model)

```
  LOCAL (dev/CI)                          EC2 (live)
  ──────────────                          ──────────
  docker-compose up the 5 services        SG/Compute `content_proxy create`
  load-vaults from a local zip            user-data: compose up + load-vaults (sgit/s3/zip)
  TUI talks to localhost                  TUI talks over SSM / the LB
  pytest: in-memory + real-chromium       deploy-via-pytest: numbered lifecycle
```

The same compose template renders both; only image refs, LB, and vault source differ.

---

## 12. The `/mitm-proxy` smoke check (MVP) + the `/pw` on `:443` path

The cheapest "is everything wired?" signal. The interceptor **always** processes `/mitm-proxy`
paths, so the FastAPI MITM service's own built-in UI gets injected and rendered — with **no
vault, no origin, no cookie, no script** deployed. If you see the UI, the chain works.

```
  Browser ──proxy──▶ mitmproxy-(ext|int) ──always-process──▶ FastAPI MITM service
   GET /mitm-proxy        (addon)                              serves its admin/UI
        ◀───────────────  injected UI page  ◀──────────────── (modified_body)
        │
        ▼  the UI renders  ⇒  mitmproxy ✓  interceptor ✓  FastAPI ✓  browser path ✓
```

And the browser-to-Playwright path is **always** through the vault on `:443`:

```
  Vault page (https://<host>, :443)
        │  fetch('/pw/sequence/execute')          ← same-origin, no mixed content
        ▼
  vault-app :443  ──/pw──▶  sg-playwright :8000   ← reverse proxy (X-Forwarded-Prefix: /pw,
        ▲                                            x-sgraph-access-token → X-API-Key)
        │  https only
  (sg-playwright :8000 is never exposed to the browser directly)
```

---

## 13. TLS termination (Let's Encrypt / ACM)

```
  LOCAL                         EC2 — Let's Encrypt            EC2 — AWS ACM
  ─────                         ───────────────────            ─────────────
  vault-app self-signed         vault-app self-terminates      ALB terminates TLS (ACM cert)
  (NONE) on :443                :443 with LE cert (IP/DNS)         │
        │                              │                          ▼
   browser accepts warning        browser trusts LE          vault-app behind ALB (http)
```

Choice carried by `Schema__Content_Proxy__Create__Request.tls`
(`Enum__Content_Proxy__Tls ∈ {NONE, LETSENCRYPT, ACM}`). Prior art for the LE path:
`team/roles/architect/reviews/05/14/v0.2.6__vault-app-tls-options.md`.
</content>
