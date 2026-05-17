---
title: "08 — Decisions applied (Dev entry point)"
file: 08__decisions-applied.md
author: Architect (Claude — code-web session)
date: 2026-05-17 (UTC hour 00)
parent: README.md
status: READ FIRST. Compact index of every gating question, the human's verbatim decision, and the plan file(s) it touched.
---

# 08 — Decisions applied

This is the Dev's one-page entry point. Every question (Q1–Q17) is listed below with the human's resolution and the plan files it modifies. After scanning this, jump to `04__phased-implementation.md` for the work.

---

## Headline decisions

1. **Plan version is v0.2.23** (after `dev` merge resolved the `vDONT-MERGE` placeholder). Plan folder: `v0.2.23__plan__vault-publish-spec/`. Spec `version` starts at `v0.1.0`.
2. **Sequencing: v2 vault-publish ships FIRST**, fully sequential. Lab-brief work is post-v2.
3. **Subdomain scheme: FLAT** — `<slug>.aws.sg-labs.app`. No namespace concept in v2.
4. **Cert: existing wildcard** `*.aws.sg-labs.app`, ARN `arn:aws:acm:us-east-1:745506449035:certificate/99346343-dc1e-4a62-a6d3-0f22ab7bfffa` (Issued in `us-east-1`). Bootstrap consumes it via `--cert-arn`; no cert work for v2.
5. **Bootstrap is singular**, not per-namespace. One CloudFront distribution, one Function URL, one cert ARN. SSM keys: `/sg-compute/vault-publish/bootstrap/{cloudfront-distribution-id, lambda-name, zone, cert-arn, waker-function-url}`.
6. **Phase 0 = COMPLETED 2026-05-17.** Empirically verified end-to-end. Dev starts at **P1a**.
7. **Phase 1a first commit = fix `Vault_App__Service.delete_stack` to delete the per-slug A record** (Q13 gating audit confirmed the leak).

---

## Per-question index

| Q | Decision (verbatim) | Files touched |
|---|---------------------|---------------|
| Q1 | **Sequential, v2 first.** Build the full v2 vault-publish (this plan, P1a → P2d) FIRST. Lab-brief work happens AFTER v2 lands. NOT parallel. | `04` (cross-phase deps section), `06` (Q1 RESOLVED), `README` |
| Q2 | **B — re-author** slug primitives from brief spec. ~4 small files. | `04` (P1b risks), `06` (Q2 RESOLVED) |
| Q3 | **Confirmed** — IAM policy edit lands in `Ec2__AWS__Client.py`. We own it. | `04` (P1a scope row already correct), `06` (Q3 RESOLVED) |
| Q4 | **v0.2.23** repo version (from `dev` merge). Plan folder name aligned. Spec `version` = `v0.1.0`. | Folder name, `01 §11`, `06` (Q4 RESOLVED), `README` |
| Q5 | **C** — add only `SUBDOMAIN_ROUTING` to `Enum__Spec__Capability`. Reuse `VAULT_WRITES` + `CONTAINER_RUNTIME` for the other two. | `03 §A.3`, `06` (Q5 RESOLVED) |
| Q6 | **Parallel within Phase 2** (B). Two Devs: (2a) and (2b → 2c); 2d waits on both. | `04` (cross-phase deps diagram), `06` (Q6 RESOLVED) |
| Q7 | **A — consume existing ARN.** Bootstrap takes `--cert-arn <existing wildcard ARN>`. | `04` (P2d scope + risks), `07 §2`, `06` (Q7 RESOLVED) |
| Q8 | **A** — Function URL `auth_type='NONE'` for v2; OAC verifier as phase-2d-followup. | `04` (P2d scope), `06` (Q8 RESOLVED) |
| Q9 | **A** — write into `v0.1.31/01__playwright-service.md` (un-migrated); create new entries for vault-publish under same un-migrated tree. | `04` (Reality-doc update notes in P1a/P1b/P2a), `06` (Q9 RESOLVED) |
| Q10 | **SSM-only** for bootstrap pinned IDs. No local file. Singular keys (no `<namespace>` segment). | `04` (P2d risks), `07 §4.3`, `06` (Q10 RESOLVED) |
| Q11 | Informational. Underscore for package, hyphen for CLI. No decision needed. | `06` (Q11 INFORMATIONAL) |
| Q12 | **Defer reaper.** Operator uses existing `sg aws dns records delete`. | `07 §3.4`, `06` (Q12 RESOLVED) |
| Q13 | **Confirmed: per-slug A record MUST be deleted on node delete.** Audit confirmed `delete_stack` leaks. Wire deletion into `delete_stack` as P1a's first commit. | `01 §13.4`, `04` (P1a gating note), `07 §3.5`, `06` (Q13 RESOLVED, GATING) |
| Q14 | **Defer** (cross-account, future). | `07 §4.2`, `06` (Q14 RESOLVED) |
| Q15 | **Generous seed**: `www`, `api`, `admin`, `status`, `mail`, `cdn`, `auth`. No namespace tokens (flat scheme). | `04` (P1b domain addendum), `07 §1.4`, `06` (Q15 RESOLVED) |
| Q16 | **Collapsed by the flat-scheme decision.** Existing cert covers v2. Labs use a separate delegated zone post-v2. | `07 §2.5`, `06` (Q16 RESOLVED) |
| Q17 | **Lab-zone provisioning (NEW).** Post-v2, lab spec gets its own delegated zone (e.g., `lab.sg-labs.app`) with its own wildcard cert. Not v2 scope. | `07 §2.5 / §1.3`, `06` (Q17 RESOLVED, new) |

---

## Structural simplifications from the flat-scheme decision

The flat scheme (`<slug>.aws.sg-labs.app`, decided 2026-05-17) collapses several previously-planned artefacts:

| Artefact | Status |
|----------|--------|
| `Enum__Sg_Labs__Namespace` | **DELETED** from plan. Flat scheme has no namespace concept. |
| `Schema__Subdomain__Parts` | **DELETED** from plan. `Slug__From_Host` returns `Safe_Str__Slug` directly. |
| `namespace` field on `Schema__Vault_Publish__Register__Request` | **DELETED** from plan. |
| `namespace` field on `Schema__Vault_Publish__Bootstrap__Request` | **DELETED** from plan. |
| `Fqdn__Builder` helper class | **DELETED** from plan. FQDN computed inline in `register`. |
| Per-namespace cert provisioning | **DELETED** — one existing wildcard covers v2. |
| Per-namespace SSM key segment | **DELETED** — SSM keys are singular. |
| Per-namespace bootstrap runs | **DELETED** — bootstrap is singular. |

Net: ~3–4 fewer files in `sg_compute_specs/vault_publish/`, simpler bootstrap schema, simpler SSM layout, simpler Waker `Slug__From_Host` return type.

---

## Empirical anchor — Phase 0 evidence (2026-05-17)

```bash
sg vault-app create --with-aws-dns --name hello-world --wait
```

| Field | Value |
|-------|-------|
| Instance ID | `i-05c161bc8aae48b01` |
| Public IP | `18.130.98.215` |
| FQDN | `hello-world.sg-compute.sgraph.ai` |
| Wall-clock to healthy | 1 min 54 s |
| TLS issuer | Let's Encrypt R13 (CA-signed) |
| Cert remaining | 89 days |
| Auto-DNS log | `auto-dns: done … (INSYNC + authoritative)` in 24190 ms |

The warm path works end-to-end on the substrate; the v2 plan is composition over verified primitives.

---

## What Dev does next

1. Read `01__grounding.md` — confirm understanding of what exists today (esp. §13 Phase 0 evidence).
2. Read `02__reuse-map.md` — confirm understanding of REUSE / EXTEND / NEW vocabulary.
3. Read `03__delta-from-lab-brief.md` — apply A.1 through A.13 corrections to any brief code copied verbatim.
4. **Read `04__phased-implementation.md`** — the per-phase work checklist. Start P1a.
5. Read `05__test-strategy.md` — no mocks, in-memory composition, parametrise over `SG_AWS__DNS__DEFAULT_ZONE`.
6. Reference `07__domain-strategy.md` whenever DNS / cert / SSM-keys questions arise.
7. Reference `06__open-questions.md` when investigating "why did the Architect choose X" — the historical context is preserved there.

**Dev does NOT need to re-litigate any of Q1–Q17.** They are all RESOLVED. If a new question arises during implementation, file it as Q18+ in `06__open-questions.md` and surface to Architect before proceeding.
