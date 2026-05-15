---
title: "QA Vault-App — briefing pack"
version: v0.2.6
date: 2026-05-15
status: PROPOSED — the substrate exists today; the QA vault-app itself is what this pack proposes
audience: Architect, Dev, QA, Librarian (cross-role)
supersedes (in part):
  - team/humans/dinis_cruz/claude-code-web/05/13/21/v0.2.6__arch-plan__qa-service.md
  - team/humans/dinis_cruz/claude-code-web/05/14/01/v0.2.6__arch-plan__vault-app-stack__v2-delta.md
---

# QA Vault-App — Briefing Pack

A self-contained briefing pack for the **next slice**: building the QA Util as
a vault-resident app on top of the vault-app substrate this branch just
shipped. Three files, read in order:

| # | File | What it covers | Audience |
|---|------|---------------|----------|
| 00 | this file               | Pack overview, the journey so far, where the QA Util fits, **status table** | everyone — read first |
| 01 | `01__what-exists-today.md` | The substrate this branch shipped: `vault-app` spec, 4-container stack, TLS, ACME, Playwright API, mitmproxy, host-plane, CLI surface | Dev / Architect picking up the next slice |
| 02 | `02__qa-app-design.md`    | The QA vault-app design: what runs inside the vault, scenario / assertion shape, evaluator, slice plan, open questions | Dev / Architect writing the QA vault-app code |

---

## The journey in one paragraph

The v0.27.38 brief (12 May 2026) called for a "QA Stack on SG/Compute". The
first architect plan (v1, 13 May) proposed embedding QA-specific code
(scenarios, assertions, evaluator, routes) **inside this repo's playwright
service**. The v2 delta (14 May) rejected that framing and reframed the
work: **this repo ships a generic vault-app *substrate*; QA is one
vault-app that runs on top of it**. The substrate is what this branch
(`claude/architect-qa-service-ijc61`) shipped — vault-app spec, 4-container
compose, TLS-by-default, Let's Encrypt IP certs, externally-reachable
Playwright API, mitmweb access via SSM, the lot. The **QA vault-app itself
has not been built**. That is what this pack proposes.

---

## The reframe is load-bearing

Read it again from the v2 delta:

> The stack is not a QA stack. It is a generic execution substrate for any
> vault-resident app (`vault_app`) needing persistent vault storage, browser
> automation, and a transparent capturing proxy. QA is the first vault-app;
> other use cases (traffic simulation, scraping, agent workbench, regression
> harnesses) follow the same shape and reuse the same stack image.

Consequences this pack inherits:

- **No QA-specific schemas land in `sg_compute_specs/playwright/`** —
  `Schema__QA__Scenario`, `Schema__QA__Assertion__*`, etc. all live in the
  QA vault-app's own codebase (which is a vault repo, not this one).
- **No `Routes__QA` on the playwright FastAPI.** Scenarios and assertions
  are the QA app's concern; it composes existing `/sequence/execute` calls
  with its own assertion logic.
- **No QA scheduler in `sg_compute_specs/`.** Scheduling happens
  out-of-EC2 (or as a future plain-CLI thing); not part of the substrate.

The substrate gives the QA app: vault storage, browser automation,
transparent traffic capture, an authenticated API surface. Everything QA-
specific (scenario format, assertion language, run results, reports)
belongs in the QA vault-app itself.

---

## Status table — the 11 original acceptance criteria

From the v0.27.38 source brief, against what exists today and what's still
to do:

| # | Original AC | Status | Where it lives now |
|---|-------------|--------|---|
| 1 | Vault scenario editor (App Mode)             | ❌ not built       | QA vault-app (this pack §02) |
| 2 | Iframe-injection execution mode              | ❌ not in scope    | QA vault-app's *client* concern; substrate is unaware |
| 3 | Real-browser Playwright execution            | ✅ **substrate**   | `POST /sequence/execute` (since v0.1.32+; externally reachable on `:11024` after this branch) |
| 4 | Structured JSON results per run              | 🟡 partial         | `Schema__Sequence__Response` exists; needs QA-side wrapping with assertion verdicts (§02 slice 1) |
| 5 | One-command deploy of QA stack               | ✅ **substrate**   | `sp vault-app create --with-playwright --wait` |
| 6 | 5-minute scheduling loop                     | ❌ deferred        | Out-of-EC2 orchestration; not in this pack |
| 7 | Daily-summary generator                      | ❌ deferred        | QA vault-app, post-MVP |
| 8 | MITM network-log capture per run             | 🟡 partial         | mitmproxy capture exists + reachable via `/web/`; per-run-id keying needs a small sidecar slice (§02 slice 4) |
| 9 | Browser isolation per run                    | ✅ **substrate**   | Each `/sequence/execute` call gets a fresh Chromium process |
| 10 | Static projections / reports in vault       | ❌ deferred        | QA vault-app, post-MVP |
| 11 | Assertions vocabulary (`url_contains`, …)   | ❌ not built       | QA vault-app (this pack §02 slice 2) |

**Substrate: 4 of 11 done (✅), 2 partial (🟡), 5 belong to the QA vault-app
itself (❌, defined in §02 of this pack).**

---

## Why a pack and not one file

Three concerns, three readers:

- **Dev picking up the next slice** wants to know what's already in place
  — files, services, CLI verbs, env vars. That's `01__what-exists-today.md`.
- **Architect deciding the QA app's shape** wants the design, not the
  substrate recap. That's `02__qa-app-design.md`.
- **Anyone returning to the project in three months** wants the
  journey-in-one-paragraph plus the status table. That's this file.

Keep them separate so each reader can stop after the file that matches their
question.

---

## Cross-references

The substrate work shipped under these key paths:

| What | Where |
|---|---|
| Vault-app spec | `sg_compute_specs/vault_app/` |
| Compose template | `sg_compute_specs/vault_app/service/Vault_App__Compose__Template.py` |
| TLS library | `sg_compute/platforms/tls/` |
| §8.2 TLS launch contract | `sg_compute/fast_api/Fast_API__TLS__Launcher.py` |
| CLI surface | `sg_compute_specs/vault_app/cli/Cli__Vault_App.py` |
| Agent-facing Playwright API guide | `library/guides/v0.2.6__playwright-api-for-agents.md` |
| Vault-Dev-team contract brief | `team/comms/briefs/v0.2.6__sg-send-vault-tls-contract.md` |
| sgit-CLI two-auth-headers brief | `team/comms/briefs/v0.2.6__sgit-cli-two-auth-headers.md` |
| Vault → Playwright API brief | `team/comms/briefs/v0.2.6__vault-to-playwright-api.md` |
| Closing debrief | `team/claude/debriefs/2026-05-15__vault-app-tls-letsencrypt-ip.md` |

Source briefs that this pack supersedes:

- `team/humans/dinis_cruz/claude-code-web/05/13/21/v0.2.6__arch-plan__qa-service.md` (v1 — embedded QA-in-this-repo framing; replaced)
- `team/humans/dinis_cruz/claude-code-web/05/14/01/v0.2.6__arch-plan__vault-app-stack__v2-delta.md` (v2 — the reframe; substrate parts delivered; QA-vault parts captured in §02 of this pack)

---

*Filed at the close of the v0.2.6 vault-app substrate slice. The QA Util as
the first vault-app on it is the next slice.*
