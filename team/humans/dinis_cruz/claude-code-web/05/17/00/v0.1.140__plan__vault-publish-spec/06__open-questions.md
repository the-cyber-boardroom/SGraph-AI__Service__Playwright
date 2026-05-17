---
title: "06 — Open questions for the human"
file: 06__open-questions.md
author: Architect (Claude — code-web session)
date: 2026-05-17 (UTC hour 00)
parent: README.md
---

# 06 — Open questions

Decisions the human must rule on before Dev picks up. Ordered by **blockingness** — Q1 / Q2 / Q3 block phase 1; Q4 / Q5 are cosmetic-ish but should be settled before too much code lands; Q6+ are nice-to-have clarifications.

---

## Q1 — Is the brief's "lab-brief lands first" expectation binding?

**Context:** the lab-brief recommends landing its P0+P1 (DNS-only experiments) *before* any v2 vault-publish Dev work, on the theory that the DNS specific-record-beats-wildcard claim is the load-bearing assumption of the whole v2 architecture and should be measured first.

**The vault-publish plan does NOT depend on the lab.** Phase 1a and Phase 1b can ship without any lab work; phase 2d's "DNS swap converges" claim is verified by the integration test in `05__test-strategy.md §5.1` (`test_6`).

**Two options:**

| Opt | Position |
|-----|----------|
| A | Land lab P0+P1 first (1 dev-week). Get measurement-backed answers to Q1/Q2 (lab-brief §1). Then start v2 Phase 1a. |
| B | Skip the lab. Start v2 Phase 0 → 1a → 1b in parallel with whoever can pick up the lab later. Use the integration test in phase 2d as the empirical validation. |

**Architect's recommendation:** **B**. The lab is excellent work but it does not unblock v2; the v2 integration test in phase 2d covers the load-bearing claim end-to-end. The lab is best landed *after* phase 1b so it can use the real `sg vp` registry as a backing store for E27. The lab and the v2 brief should be **siblings**, not **sequential**.

**Human, please pick A or B.** This decides whether Dev starts on the lab or on `vault-app stop/start`.

---

## Q2 — Cherry-pick the slug primitives from `claude/review-subdomain-workflow-bRIbm`, or re-author?

**Context:** see grounding §6.1. The brief assumes Dev "ports" `Safe_Str__Slug`, `Slug__Validator`, `Reserved__Slugs`, `Enum__Slug__Error_Code` and their tests from a top-level `vault_publish/` Python package — but that package only exists on the `claude/review-subdomain-workflow-bRIbm` branch, not on `dev`.

**Three options:**

| Opt | Position |
|-----|----------|
| A | Cherry-pick from `claude/review-subdomain-workflow-bRIbm` into the new spec folder via `git cherry-pick` on specific commits (`c184867`, `23c2800`, `2335cee`). Verify each file still complies with current Type_Safe / Safe_Str conventions; rewrite if drifted. |
| B | Re-author from the brief's specification ([`04 §3`](file:///tmp/vault-publish-brief/04__vault-publish-spec.md) has regex, max-length, error-code list). About 4 small files + their tests; ~half a day. |
| C | Land the source branch first (after `library/dev_packs/v0.2.11__vault-publish/` is fully retired), then port. Adds an unrelated merge dance. |

**Architect's recommendation:** **B** — re-author. The source surface is tiny (4 files), the brief's specification is complete, and we avoid pulling in any dead code from the v0.2.11 design that crept into those files. Faster than auditing.

---

## Q3 — Who owns the `playwright-ec2` IAM policy edit?

**Context:** the brief ([`03 §3.4`](file:///tmp/vault-publish-brief/03__sg-compute-additions.md)) places the `ec2:StopInstances` policy addition in `sgraph_ai_service_playwright__cli/deploy/SP__CLI__Lambda__Policy.py`. **But the `playwright-ec2` instance profile is built by `sgraph_ai_service_playwright__cli/ec2/service/Ec2__AWS__Client.py`** (verified — `IAM__ROLE_NAME = 'playwright-ec2'` at line 147; policy assembly around line 177). `Vault_App__Service.py:40` only *names* the profile (`PROFILE_NAME = 'playwright-ec2'`); it does not own its policy.

**The edit therefore lands in `Ec2__AWS__Client.py`, not in `vault_app/` or `deploy/`.** The brief mis-cites the owner.

**Confirm:** Dev should edit `Ec2__AWS__Client.py` and the corresponding test under `tests/unit/sgraph_ai_service_playwright__cli/ec2/service/`. The change must include the tag-condition `aws:ResourceTag/StackType=vault-app`.

**Architect's recommendation:** confirm the above; no human decision needed unless the IAM ownership should move.

---

## Q4 — Version number for the new spec + the root `version` file weirdness

**Context:** the repo-root `version` file currently reads `vDONT-MERGE.DONT-MERGE.1` (a session-marker placeholder, not a real release). The reality master index reports v0.1.140 as the codebase version; `sg_compute/version` is v0.1.162. The plan uses `v0.1.140` in its filename but a Dev shipping a new spec needs to know what `sg_compute_specs/vault_publish/version` should start at.

**Two sub-questions:**

- **Q4a** — what value should `sg_compute_specs/vault_publish/version` carry at first commit? Suggestion: `v0.1.0` (mirroring `sg_compute_specs/elastic/version` and others which are spec-versioned independently from the package).
- **Q4b** — when does the repo-root `version` file get fixed? Not in this plan's scope, but Dev will want to know which release number this work targets when bumping it at PR-merge time.

**Architect's recommendation:** Q4a — `v0.1.0`. Q4b — Historian / DevOps responsibility; out of plan scope.

---

## Q5 — `Enum__Spec__Capability` — add new members for vault-publish?

**Context:** the brief proposes `capabilities = ['subdomain-routing', 'on-demand-compute', 'tls-wildcard']`. As `03__delta-from-lab-brief.md §A.3` notes, the codebase uses `Enum__Spec__Capability` — none of those three values exist there today (would need to verify by reading the enum file; this plan assumes they do not).

**Three options:**

| Opt | Position |
|-----|----------|
| A | Add three new `Enum__Spec__Capability` members (`SUBDOMAIN_ROUTING`, `ON_DEMAND_COMPUTE`, `TLS_WILDCARD`). Per CLAUDE.md rule #20, this requires a schema-catalogue update + a logged decision. |
| B | Map to existing capabilities (e.g. `VAULT_WRITES` + `CONTAINER_RUNTIME`). Less descriptive but no schema change. |
| C | Use the closest existing capability + add ONE new one (`SUBDOMAIN_ROUTING`) — the most distinctive of the three. |

**Architect's recommendation:** **C** — add `SUBDOMAIN_ROUTING` (the genuinely new capability) + reuse `VAULT_WRITES` + `CONTAINER_RUNTIME`. The other two ("on-demand-compute", "tls-wildcard") are already implicit in the substrate.

---

## Q6 — Phase ordering: parallel vs serial within Phase 2?

**Context:** phases 2a / 2b / 2c can land in any order (per `04__phased-implementation.md` cross-phase dependencies). With a single Dev they're serial; with two Devs they parallelise.

**Two options:**

| Opt | Position |
|-----|----------|
| A | Serial — one Dev does 2a → 2b → 2c → 2d (12-day path). |
| B | Parallel — two Devs do (2a) and (2b → 2c) in parallel; 2d picks up when both are ready. |

**Architect's recommendation:** depends on staffing. If two Devs available, **B**. If one, **A**, with 2a first (the biggest rock) so the long pole is in the ground.

---

## Q7 — Should `Vault_Publish__Service.bootstrap` create the ACM cert, or always consume an existing ARN?

**Context:** the brief ([`03 §7`](file:///tmp/vault-publish-brief/03__sg-compute-additions.md), [`04 §6`](file:///tmp/vault-publish-brief/04__vault-publish-spec.md)) explicitly leaves "request the wildcard ACM cert" out of scope — bootstrap consumes an existing ARN. Operator must manually issue the cert once.

**Two options:**

| Opt | Position |
|-----|----------|
| A | Stay with the brief — bootstrap requires `--cert-arn`; manual cert issuance once. |
| B | Phase-2d-followup: extend `aws/acm/service/ACM__AWS__Client` with `request_dns_validated`, then bootstrap can mint the cert if `--cert-arn` is absent. Adds ~4 files. |

**Architect's recommendation:** **A** for v2; defer **B** to a phase-2d-followup brief. Cert issuance is rare (once per environment forever).

---

## Q8 — Lambda Function URL `auth_type` for the Waker in production?

**Context:** the brief ([`04 §5.1`](file:///tmp/vault-publish-brief/04__vault-publish-spec.md)) configures `auth_type='NONE'` because "CloudFront is the only intended caller; the Function URL is on a `*.lambda-url.<region>.on.aws` host that nobody else has the URL for". Security through obscurity — fine for the lab (lab-brief Q6), questionable for production.

**Two options:**

| Opt | Position |
|-----|----------|
| A | Follow the brief — `auth_type='NONE'` for v2 phase 2d. Land the work; add an OAC-style custom-origin-header verifier as phase-2d-followup. |
| B | Land `auth_type='AWS_IAM'` immediately with CloudFront OAC + IAM-signed origin requests. Adds ~2 days; touches the Waker authentication path. |

**Architect's recommendation:** **A** with a tracked follow-up. The Function URL is on a 12-char random hostname; brute-force discovery during the V2 phase 2d window is implausibly low-probability. Land the work, add the verifier soon after.

---

## Q9 — Reality-doc migration: domain-tree or v0.1.31/?

**Context:** per `team/roles/librarian/reality/README.md`, the reality system is migrating from `v0.1.31/NN__*.md` monoliths to per-domain `<domain>/index.md` files. The Playwright service domain has not yet migrated (per `team/roles/librarian/reality/index.md`). The vault-publish work touches three domains: `playwright-service` (peripheral — Lambda Web Adapter usage), `sg-compute/vault_app` (extended), and `sg-compute/vault_publish` (new).

**Two options:**

| Opt | Position |
|-----|----------|
| A | Write into `v0.1.31/01__playwright-service.md` (un-migrated) for vault-app changes; create new `sg-compute/vault-publish/index.md` for the new spec. |
| B | Migrate `vault_app` to the domain-tree style as part of phase 1a; then both spec updates live in the new tree. |

**Architect's recommendation:** **A**. The migration is the Librarian's responsibility (queued in `DAILY_RUN.md`); the v2 work should not blow up its scope by becoming a migration carrier.

---

## Q10 — Where does the bootstrap's pinned IDs config live?

**Context:** the brief ([`04 §6`](file:///tmp/vault-publish-brief/04__vault-publish-spec.md) step 9) says "write to local config (`.sg/vault-publish-bootstrap.json` or similar) and as SSM params `/sg-compute/vault-publish/bootstrap/{distribution-id,lambda-name,zone,cert-arn}`". File-local config rots faster than SSM (loses the machine, loses the config); SSM is the durable source of truth.

**Architect's recommendation:** SSM-only. The local file is a *cache*, not a source of truth — Dev can omit it from phase 2d entirely and the spec still works.

---

## Q11 — Naming: `vault_publish` vs `vault-publish`?

**Context:** the brief uses `sg_compute_specs/vault_publish/` (underscore — Python package) and `sg vault-publish` (hyphen — CLI). This mirrors `vault_app` / `vault-app`. The plan adopts the same convention.

**No human decision needed** — just calling it out so Dev does not invent a third spelling.

---

## Q12 — Build the stale-record reaper now or later?

**Context:** see `07__domain-strategy.md §3.4`. EC2-terminated-outside-`sg-vp` paths leave orphan A records under `*.vp.sg-labs.app`.

**Architect's recommendation:** **defer** to a phase-2d-followup. Operator can hand-clean via `sg aws dns records list` in the v2 window.

**Gating:** non-gating.

---

## Q13 — Does `Vault_App__Service.delete_stack` already delete the per-slug A record?

**Context:** see `07__domain-strategy.md §3.5`. Today's `delete_stack` (`sg_compute_specs/vault_app/service/Vault_App__Service.py:528`) needs an audit before P1a's `stop_stack` is implemented — `stop_stack`'s DNS-delete behaviour should mirror `delete_stack`'s, and if `delete_stack` doesn't delete, every terminated stack to date has leaked an A record.

**Action:** Dev audits at the very start of P1a. If absent: file a substrate-bug debrief (CLAUDE.md rule #27 — bad failure), fix in P1a, run a one-shot cleanup pass against the existing zone.

**Architect's recommendation:** confirm the audit happens; no human decision needed.

**Gating:** **GATING for P1a.** Discovered as a side effect of writing the domain strategy. Must be answered before P1a Dev work starts.

---

## Q14 — Cross-account hosted zones?

**Context:** see `07__domain-strategy.md §4.2`. Single-account assumption today.

**Architect's recommendation:** defer; park in `library/roadmap/`. Not a phase-2d concern.

**Gating:** non-gating.

---

## Q15 — Generous or minimal seed for `Reserved__Slugs` shadow list?

**Context:** see `07__domain-strategy.md §1.5` and Q15 in `07`. The namespace strings (`vp`, `lab`) must be reserved as leaves. Should the seed also include common labels (`www`, `api`, `admin`, `status`, `mail`, `cdn`, `auth`)?

**Architect's recommendation:** **generous seed** (Option A in `07`). Cheaper to release a slug later than to migrate a wrongly-claimed one.

**Gating:** non-gating, but settle before P1b ships so test data is right.

---

## Q16 — Does v2 phase 2d provision the `*.lab.sg-labs.app` wildcard cert, or wait for the lab spec?

**Context:** see `07__domain-strategy.md §7 Q16`. Bootstrap is per-namespace; certs are independent.

**Architect's recommendation:** v2 provisions only `*.vp.sg-labs.app`. Lab spec, when it lands, provisions its own.

**Gating:** non-gating (lab is sibling track per Q1).

---

## Summary — what Dev needs answered to start

The six answers that gate phase 1a:

- **Q1 — Lab first or v2 first?** → Architect recommends v2 first; **PLEASE CONFIRM**.
- **Q2 — Slug primitives: cherry-pick or re-author?** → Architect recommends re-author; **PLEASE CONFIRM**.
- **Q3 — Confirm `Ec2__AWS__Client.py` owns the IAM policy edit?** → Architect recommends yes; **PLEASE CONFIRM**.
- **Q4a — Spec `version` starts at `v0.1.0`?** → Architect recommends yes; **PLEASE CONFIRM**.
- **Q5 — Add `Enum__Spec__Capability.SUBDOMAIN_ROUTING`?** → Architect recommends yes (Option C); **PLEASE CONFIRM**.
- **Q13 — Audit `Vault_App__Service.delete_stack` for DNS-delete behaviour.** → Dev action; no human decision needed beyond confirming the audit happened. **GATING for P1a.**

Q6 – Q10 and Q12 / Q14 / Q15 / Q16 can be revisited per phase as Dev encounters them.

---

## Once these are answered

Dev contract is:

- Read this plan front-to-back (`README.md` → `01` → `02` → `03` → `04` → `05` → `06`).
- Start Phase 1a per `04__phased-implementation.md`.
- For every PR, file the debrief under `team/claude/debriefs/` and update the reality-doc per CLAUDE.md rules #26-28.
- For every architectural deviation (e.g. discovering an existing class that obsoletes a NEW file in `02__reuse-map.md`), file an addendum review under `team/roles/architect/reviews/05/<DD>/` and prompt the Architect to update this plan.
