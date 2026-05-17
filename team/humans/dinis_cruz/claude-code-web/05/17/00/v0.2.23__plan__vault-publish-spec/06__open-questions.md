---
title: "06 — Open questions for the human (ALL RESOLVED 2026-05-17)"
file: 06__open-questions.md
author: Architect (Claude — code-web session)
date: 2026-05-17 (UTC hour 00; resolved 2026-05-17)
parent: README.md
status: ALL gating questions RESOLVED. Dev can start at P1a — see `08__decisions-applied.md`.
---

# 06 — Open questions

All Q1–Q17 are RESOLVED. Each question carries a **RESOLVED** banner up top with the human's decision; original context follows underneath as historical record.

---

## Q1 — Is the brief's "lab-brief lands first" expectation binding?

> **RESOLVED 2026-05-17 — Sequential, v2 first.** Build the full v2 vault-publish (this plan, P1a → P2d) FIRST. Lab-brief work happens AFTER v2 lands. NOT parallel. (Stronger than Architect's Option B.)

**Context:** the lab-brief recommends landing its P0+P1 (DNS-only experiments) *before* any v2 vault-publish Dev work, on the theory that the DNS specific-record-beats-wildcard claim is the load-bearing assumption of the whole v2 architecture and should be measured first.

**The vault-publish plan does NOT depend on the lab.** Phase 1a and Phase 1b can ship without any lab work; phase 2d's "DNS swap converges" claim is verified by the integration test in `05__test-strategy.md §5.1` (`test_6`).

**Two options:**

| Opt | Position |
|-----|----------|
| A | Land lab P0+P1 first (1 dev-week). Get measurement-backed answers to Q1/Q2 (lab-brief §1). Then start v2 Phase 1a. |
| B | Skip the lab. Start v2 Phase 0 → 1a → 1b in parallel with whoever can pick up the lab later. Use the integration test in phase 2d as the empirical validation. |

**Architect's recommendation:** B. The human's final decision (above) is stronger: fully sequential, v2 first.

---

## Q2 — Cherry-pick the slug primitives from `claude/review-subdomain-workflow-bRIbm`, or re-author?

> **RESOLVED 2026-05-17 — Option B: re-author** slug primitives from brief spec. ~4 small files.

**Context:** see grounding §6.1. The brief assumes Dev "ports" `Safe_Str__Slug`, `Slug__Validator`, `Reserved__Slugs`, `Enum__Slug__Error_Code` and their tests from a top-level `vault_publish/` Python package — but that package only exists on the `claude/review-subdomain-workflow-bRIbm` branch, not on `dev`.

**Three options:**

| Opt | Position |
|-----|----------|
| A | Cherry-pick from `claude/review-subdomain-workflow-bRIbm` via `git cherry-pick`. |
| B | Re-author from the brief's specification ([`04 §3`](file:///tmp/vault-publish-brief/04__vault-publish-spec.md)). |
| C | Land the source branch first, then port. |

**Architect's recommendation:** B — re-author. Matches the resolution.

---

## Q3 — Who owns the `playwright-ec2` IAM policy edit?

> **RESOLVED 2026-05-17 — Confirmed.** IAM policy edit lands in `Ec2__AWS__Client.py`. We own it.

**Context:** the brief ([`03 §3.4`](file:///tmp/vault-publish-brief/03__sg-compute-additions.md)) places the `ec2:StopInstances` policy addition in `sgraph_ai_service_playwright__cli/deploy/SP__CLI__Lambda__Policy.py`. **But the `playwright-ec2` instance profile is built by `sgraph_ai_service_playwright__cli/ec2/service/Ec2__AWS__Client.py`** (verified — `IAM__ROLE_NAME = 'playwright-ec2'` at line 147; policy assembly around line 177).

The change must include the tag-condition `aws:ResourceTag/StackType=vault-app`.

---

## Q4 — Version number for the new spec + the root `version` file weirdness

> **RESOLVED 2026-05-17 — v0.2.23.** The repo-root `version` showing `vDONT-MERGE...` was a versioning bug; pulling `dev` into the branch resolves it to v0.2.23. Plan folder is named `v0.2.23__plan__vault-publish-spec`. Spec `version` file (`sg_compute_specs/vault_publish/version`) starts at `v0.1.0`.

**Context:** the repo-root `version` file currently reads `vDONT-MERGE.DONT-MERGE.1` (a session-marker placeholder). After `dev` merge, real value is v0.2.23.

- **Q4a** — `sg_compute_specs/vault_publish/version` starts at `v0.1.0`.
- **Q4b** — repo-root `version` is fixed by the `dev` merge; not in this plan's scope to bump.

---

## Q5 — `Enum__Spec__Capability` — add new members for vault-publish?

> **RESOLVED 2026-05-17 — Option C.** Add only `SUBDOMAIN_ROUTING` to `Enum__Spec__Capability`. Reuse `VAULT_WRITES` + `CONTAINER_RUNTIME` for the other two.

**Context:** the brief proposes `capabilities = ['subdomain-routing', 'on-demand-compute', 'tls-wildcard']`. None of those three values exist as enum members today.

**Three options:**

| Opt | Position |
|-----|----------|
| A | Add three new `Enum__Spec__Capability` members. |
| B | Map all three to existing capabilities. |
| C | Add ONE new (`SUBDOMAIN_ROUTING`) + reuse existing for the other two. |

Per CLAUDE.md rule #20, adding the new enum member requires a schema-catalogue update + a logged decision.

---

## Q6 — Phase ordering: parallel vs serial within Phase 2?

> **RESOLVED 2026-05-17 — Option B: parallel within Phase 2.** Two Devs: (2a) and (2b → 2c); 2d waits on both.

**Context:** phases 2a / 2b / 2c can land in any order (per `04__phased-implementation.md` cross-phase dependencies).

**Two options:**

| Opt | Position |
|-----|----------|
| A | Serial — one Dev does 2a → 2b → 2c → 2d (~12-day path). |
| B | Parallel — two Devs do (2a) and (2b → 2c) in parallel; 2d picks up when both ready (~8-day path). |

---

## Q7 — Should `Vault_Publish__Service.bootstrap` create the ACM cert, or always consume an existing ARN?

> **RESOLVED 2026-05-17 — Option A: consume existing ARN.** Cert already exists: `arn:aws:acm:us-east-1:745506449035:certificate/99346343-dc1e-4a62-a6d3-0f22ab7bfffa` covering `*.aws.sg-labs.app`. Bootstrap takes `--cert-arn`.

**Context:** the brief explicitly leaves "request the wildcard ACM cert" out of scope — bootstrap consumes an existing ARN. Operator must manually issue the cert once.

**Two options:**

| Opt | Position |
|-----|----------|
| A | Stay with the brief — bootstrap requires `--cert-arn`. |
| B | Phase-2d-followup: extend `ACM__AWS__Client` to mint the cert if absent. |

---

## Q8 — Lambda Function URL `auth_type` for the Waker in production?

> **RESOLVED 2026-05-17 — Option A.** Function URL `auth_type='NONE'` for v2; OAC verifier as phase-2d-followup.

**Context:** the brief configures `auth_type='NONE'` because "CloudFront is the only intended caller; the Function URL is on a `*.lambda-url.<region>.on.aws` host that nobody else has the URL for". Security through obscurity — fine for v2; OAC custom-origin-header verifier deferred.

---

## Q9 — Reality-doc migration: domain-tree or v0.1.31/?

> **RESOLVED 2026-05-17 — Option A.** Write into `v0.1.31/01__playwright-service.md` (un-migrated); create new entries for vault-publish under the same un-migrated tree.

**Context:** the reality system is migrating from `v0.1.31/NN__*.md` monoliths to per-domain `<domain>/index.md` files. The Playwright service domain has not yet migrated.

**Two options:**

| Opt | Position |
|-----|----------|
| A | Write into un-migrated `v0.1.31/01__playwright-service.md` for vault-app changes; create new entry for vault-publish under same tree. |
| B | Migrate `vault_app` to domain-tree style as part of phase 1a. |

---

## Q10 — Where does the bootstrap's pinned IDs config live?

> **RESOLVED 2026-05-17 — SSM-only** for bootstrap pinned IDs. No local file.

**Context:** the brief says "write to local config (`.sg/vault-publish-bootstrap.json` or similar) and as SSM params". File-local config rots faster than SSM (loses the machine, loses the config); SSM is the durable source of truth.

Under the flat scheme: SSM keys are `/sg-compute/vault-publish/bootstrap/{cloudfront-distribution-id, lambda-name, zone, cert-arn, waker-function-url}` (no `<namespace>` segment).

---

## Q11 — Naming: `vault_publish` vs `vault-publish`?

> **INFORMATIONAL — no decision needed.** Underscore for Python package, hyphen for CLI verb. Mirrors `vault_app` / `vault-app`.

The plan adopts the same convention. Calling it out so Dev does not invent a third spelling.

---

## Q12 — Build the stale-record reaper now or later?

> **RESOLVED 2026-05-17 — Defer reaper.** Substrate already has `sg aws dns records delete` for purging unused records (verified at `sgraph_ai_service_playwright__cli/aws/dns/cli/Cli__Dns.py:1022-1054`). Operator-driven cleanup is acceptable for v2.

**Context:** see `07__domain-strategy.md §3.4`. EC2-terminated-outside-`sg-vp` paths leave orphan A records.

**Gating:** non-gating.

---

## Q13 — Does `Vault_App__Service.delete_stack` already delete the per-slug A record?

> **RESOLVED 2026-05-17 — Confirmed: per-slug A record MUST be deleted on node delete.** Audited: `delete_stack` (`sg_compute_specs/vault_app/service/Vault_App__Service.py:528-546`) does NOT currently delete DNS — leaks A records. Substrate already supports the deletion via `sg aws dns records delete`. P1a's first commit wires the deletion path into `delete_stack`; `stop_stack` then mirrors it.

**Action:** Dev fixes `delete_stack` as the first commit of P1a per CLAUDE.md rule #27 (bad failure caught early).

**Gating:** **GATING for P1a.**

---

## Q14 — Cross-account hosted zones?

> **RESOLVED 2026-05-17 — Defer** (cross-account, future). Park in `library/roadmap/`.

**Context:** see `07__domain-strategy.md §4.2`. Single-account assumption today.

**Gating:** non-gating.

---

## Q15 — Generous or minimal seed for `Reserved__Slugs` shadow list?

> **RESOLVED 2026-05-17 — Generous seed.** `Reserved__Slugs` seed: `www`, `api`, `admin`, `status`, `mail`, `cdn`, `auth`. No namespace tokens (flat scheme has no namespace concept).

**Context:** see `07__domain-strategy.md §1.5`. Cheaper to release a slug later than to migrate a wrongly-claimed one.

**Gating:** non-gating, but settled before P1b ships so test data is right.

---

## Q16 — Does v2 phase 2d provision the `*.lab.sg-labs.app` wildcard cert, or wait for the lab spec?

> **RESOLVED 2026-05-17 — Collapsed by the flat-scheme decision.** Existing cert (`*.aws.sg-labs.app`, single ARN above) covers v2 fully. Labs land in a **separate delegated zone** post-v2 with their **own** wildcard cert. See Q17.

**Gating:** non-gating (lab is sequential, post-v2, per Q1).

---

## Q17 — Lab-zone provisioning (NEW, captured 2026-05-17)

> **RESOLVED 2026-05-17 — Separate zone when labs land.** Post-v2, the lab spec gets its own delegated zone (e.g., `lab.sg-labs.app`) with its own wildcard ACM cert. Clean separation — no slug-name collisions with vault-publish.

**Context:** the flat scheme `<slug>.aws.sg-labs.app` (decided 2026-05-17) reserves the `aws.sg-labs.app` zone for vault-publish v2 only. Labs cannot share the same wildcard cert (would risk slug collisions and namespace conflicts).

**Implementation note (forward-only — NOT v2 scope):** when the lab spec ships, it provisions its own delegated zone + wildcard cert via the same `Route53__AWS__Client` + manual ACM cert issuance pattern. The lab spec's bootstrap consumes that ARN exactly the way vault-publish v2's bootstrap consumes `*.aws.sg-labs.app`.

**Gating:** non-gating; deferred to post-v2 lab work.

---

## Summary — All gating questions resolved; Dev can start

All Q1–Q17 are resolved. The gating set for P1a:

- **Q1 — v2 first, sequential.** RESOLVED.
- **Q2 — Re-author slug primitives.** RESOLVED.
- **Q3 — `Ec2__AWS__Client.py` owns IAM edit.** RESOLVED.
- **Q4a — Spec `version` starts `v0.1.0`.** RESOLVED.
- **Q5 — Add `SUBDOMAIN_ROUTING` only.** RESOLVED.
- **Q13 — Fix `delete_stack` DNS-delete as P1a's first commit.** RESOLVED.

Non-gating decisions (Q6 / Q7 / Q8 / Q9 / Q10 / Q12 / Q14 / Q15 / Q16 / Q17): also resolved.

**Dev contract:**

- Read `08__decisions-applied.md` first (the resolved-decisions index).
- Then read this plan front-to-back (`README.md` → `01` → `02` → `03` → `04` → `05` → `07`).
- Start Phase 1a per `04__phased-implementation.md`.
- For every PR, file the debrief under `team/claude/debriefs/` and update the reality-doc per CLAUDE.md rules #26-28.
- For every architectural deviation (e.g. discovering an existing class that obsoletes a NEW file in `02__reuse-map.md`), file an addendum review under `team/roles/architect/reviews/05/<DD>/` and prompt the Architect to update this plan.
