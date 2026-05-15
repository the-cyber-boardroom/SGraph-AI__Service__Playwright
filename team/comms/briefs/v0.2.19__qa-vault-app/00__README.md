---
title: "QA Vault-App — briefing pack (v0.2.19, supersedes v0.2.6)"
version: v0.2.19
date: 2026-05-15
status: PROPOSED — the substrate is delivered; this pack is what to build on top.
audience: Architect, Dev, QA, Librarian (cross-role)
supersedes: team/comms/briefs/v0.2.6__qa-vault-app/
---

# QA Vault-App — Briefing Pack (v0.2.19)

A self-contained pack for **building the QA Util as a vault-resident app**
on the now-delivered `vault-app` substrate. Three files, read in order:

| # | File | What it covers |
|---|------|---|
| 00 | this file                       | Pack overview, **status table** (6 ✅ / 1 🟡 / 4 ❌), what changed since v1 |
| 01 | `01__substrate-contract.md`     | The substrate's API contract — what the QA app gets to assume |
| 02 | `02__qa-app-design.md`          | The QA app design — schemas, evaluator, slice plan, open questions |

---

## What changed since v0.2.6 (v1)

The v1 pack was correct but **mis-framed**. It read as a TODO list of
substrate gaps that needed closing before the QA app could exist. In
reality the substrate was *already done* — v1 just credited it too
conservatively. v2 fixes the framing:

- **Status table reframed.** Two ACs that v1 marked 🟡 partial are
  actually ✅ at the substrate level (structured JSON results, MITM
  capture). The remaining work in those rows is **QA-app-specific**,
  not substrate-specific.
- **01 reframed from inventory to contract.** v1 was a list of "what
  exists today." v2 is a stable *contract* the QA app builds against:
  base URLs, auth header, endpoint shapes, tag set, env conventions.
  Treat 01 as the interface, not the changelog.
- **Port 80 throughout.** v1 said Playwright was on `:11024`. It's on
  `:80` now — standard HTTP, sandbox-egress-friendly. Same flag,
  different default port.
- **The "substrate slice 4" the v1 pack requested is the only substrate
  work left** — a `/capture/network-log/{run_id}` endpoint on
  `agent_mitmproxy` for per-run network-log addressability. v1 framed
  this as one of many substrate gaps; v2 names it as the *single*
  remaining substrate item.

---

## The reframe in one sentence (still load-bearing)

> The stack is not a QA stack. It is a generic execution substrate for any
> vault-resident app (`vault_app`) needing persistent vault storage, browser
> automation, and a transparent capturing proxy. **QA is the first
> vault-app**; other use cases (traffic simulation, scraping, agent
> workbench, regression harnesses) follow the same shape and reuse the
> same stack image.

— from the v0.2.6 v2 delta (`team/humans/dinis_cruz/claude-code-web/05/14/01/v0.2.6__arch-plan__vault-app-stack__v2-delta.md`). Still the load-bearing call.

---

## Status table — the 11 original acceptance criteria

From the v0.27.38 source brief, as of v0.2.19:

| # | Original AC | Status | Why |
|---|-------------|--------|---|
| 1 | Vault scenario editor (App Mode)             | ❌ QA-app                | Scenarios are vault content; an editor is a vault-UI feature of the QA app. Substrate-neutral. |
| 2 | Iframe-injection execution mode              | ❌ out of scope          | Substrate has only real-browser. Iframe-mode is a *client* concern, not a substrate one. |
| 3 | Real-browser Playwright execution            | **✅ substrate**         | `POST /sequence/execute`. Externally reachable on **port 80** (was `:11024` in v1). |
| 4 | Structured JSON results per run              | **✅ substrate**         | `Schema__Sequence__Response` returns full per-step JSON. The QA-specific *envelope* (assertion verdicts) is a QA-app concern, not a substrate gap. |
| 5 | One-command deploy of QA stack               | **✅ substrate**         | `sp vault-app create --with-playwright --wait` — TLS-prod-LE by default; recreate / extend / delete all wired. |
| 6 | 5-min scheduling loop                        | ❌ deferred              | Out-of-EC2 orchestration; not a substrate concern. The QA app exposes an HTTP trigger; whatever calls it is the operator's choice. |
| 7 | Daily-summary generator                      | ❌ QA-app post-MVP       | Consumes vault content (run history); not a substrate feature. |
| 8 | MITM network-log capture per run             | **✅ substrate** (with one follow-up) | mitmproxy captures 100% of browser traffic; reachable via `sp vault-app open mitmweb`. Per-run *addressability* (slice 4 below) is the only remaining substrate work. |
| 9 | Browser isolation per run                    | **✅ substrate**         | Each `/sequence/execute` call spawns and tears down its own Chromium. |
| 10 | Static projections / reports                | ❌ QA-app post-MVP       | Same shape as AC7 — consumes vault content. |
| 11 | Assertions vocabulary                       | ❌ QA-app slice 2        | The assertion language is the *QA app's* type system, not the substrate's. The substrate provides every primitive the assertions evaluate against (URL, status, header, DOM via Wait_For/Get_Content). |

**Substrate: 6 of 11 done (✅). 1 has a small follow-up (mitmproxy per-run
addressability — slice 4 in 02). The other 4 are QA-app-internal — there
is no substrate work left for them.**

---

## So what's actually left?

Three things, in increasing order of size:

1. **One substrate slice** — `agent_mitmproxy` per-run capture endpoint
   (~80 lines + a test). The single substrate item this pack requests.
   Detail in `02__qa-app-design.md` §5.
2. **The QA vault-app itself** — schemas, evaluator, runner, vault I/O.
   Lives in a new sibling repo (`SGraph-AI__Service__QA-Util` or
   similar — Architect Q1 lean). Detail in `02__qa-app-design.md` §6
   (slice plan).
3. **Operator wiring per use case** — vault preload keys (which QA
   scenarios), scheduling (manual / cron / GitHub Actions / event-driven),
   environment configs. These are decisions per deployment, not code.

That's the whole forward agenda. v1 framed it as "the substrate plus a lot
of QA-specific work"; v2 frames it as "the QA-specific work, plus one
small substrate follow-up."

---

## Cross-references — the substrate the QA app consumes

The substrate work landed at these paths:

| What | Where |
|---|---|
| Vault-app spec                            | `sg_compute_specs/vault_app/` |
| Compose template                          | `sg_compute_specs/vault_app/service/Vault_App__Compose__Template.py` |
| TLS library                               | `sg_compute/platforms/tls/` |
| §8.2 TLS launch contract                  | `sg_compute/fast_api/Fast_API__TLS__Launcher.py` |
| CLI surface                               | `sg_compute_specs/vault_app/cli/Cli__Vault_App.py` |
| **Playwright API agent guide**            | `library/guides/v0.2.6__playwright-api-for-agents.md` — the file the QA runner / any agent reads to drive `/sequence/execute` |
| Vault-Dev-team contract (delivered)       | `team/comms/briefs/v0.2.6__sg-send-vault-tls-contract.md` |
| sgit-CLI two-auth-headers brief (pending sgit team) | `team/comms/briefs/v0.2.6__sgit-cli-two-auth-headers.md` |
| Vault → Playwright API brief              | `team/comms/briefs/v0.2.6__vault-to-playwright-api.md` |
| Closing debrief                           | `team/claude/debriefs/2026-05-15__vault-app-tls-letsencrypt-ip.md` |

Source briefs (superseded):

- `team/humans/dinis_cruz/claude-code-web/05/13/21/v0.2.6__arch-plan__qa-service.md` (v1 — embedded-QA-in-this-repo, rejected)
- `team/humans/dinis_cruz/claude-code-web/05/14/01/v0.2.6__arch-plan__vault-app-stack__v2-delta.md` (v2 — substrate reframe; substrate part delivered; QA part is this pack)
- `team/comms/briefs/v0.2.6__qa-vault-app/` (v1 of this pack — superseded by v0.2.19)

---

*Filed at the close of the substrate work. The QA Util as the first
vault-app on it is the next slice. Open `01__substrate-contract.md` next.*
