---
title: "08 — Open questions"
file: 08__open-questions.md
author: Architect (Claude)
date: 2026-05-16 (UTC hour 15)
parent: README.md
---

# 08 — Open questions

Decisions the human must rule on before Dev picks up. Ordered by blockingness.

---

## Q1 — Which zone do we run mutating experiments against?

The harness writes records like `lab-prop-<run-id>.<zone>`. Two options:

| Opt | Position |
|-----|----------|
| **A** | **`sg-compute.sgraph.ai`** — the existing default. Already configured for the rest of the codebase. Risk: lab records pollute a "real" zone; a misconfigured tool could conflict with a real stack name (though slugs are random + tagged). |
| **B** | **A dedicated `lab.sg-compute.sgraph.ai` zone** (or `lab.sgraph.ai`) — totally isolated. Requires a one-time `aws route53 create-hosted-zone` + delegation at the registrar. Some setup; safer; no risk of stomping anything. |

**Recommendation: B for production-grade safety, but A for "let's start tomorrow".** The harness is parameterised over the zone, so a future migration is just an env-var change. Start with A under a name-prefix convention (`lab-*` only); switch to B when convenient.

---

## Q2 — Do we ship a separate AWS account or share?

Same trade-off as Q1, scaled up. Recommendation: share the existing account in early phases, with the `Lab__Safety__Account_Guard` requiring `SG_AWS__LAB__EXPECTED_ACCOUNT_ID=<id>` set on every machine that runs mutations. A dedicated lab account can wait.

---

## Q3 — Default TTL on lab-tagged resources?

`Schema__Lab__Ledger__Entry.expires_at` defaults to `created_at + 1 hour`. Justifications:

- Long enough that no experiment butts against it (longest is E27 at ~30 min).
- Short enough that yesterday's leak is gone by the time someone notices.

Confirm: 1 hour. Alt: 30 min (riskier — could expire mid-E27 if AWS is slow), or 24 hours (more leaked-resource window).

**Recommendation: 1 h default, per-experiment override via `--ttl` flag.**

---

## Q4 — Where do lab-minted ACM certs live?

Some Tier-2 experiments need a wildcard cert in `us-east-1`. Options:

| Opt | Position |
|-----|----------|
| **A** | **Mint a per-run wildcard cert** in us-east-1 (DNS-validated against the test zone), use it for one experiment, delete it after. Adds ~5–10 min to E25/E26/E27 for cert issuance. |
| **B** | **Pre-create a shared lab wildcard cert** (`*.lab-cf.<zone>` or similar). Experiments reuse it; saves time per run; never deleted by the harness. |
| **C** | **Reuse the v2 production cert** (`*.sg-compute.sgraph.ai`). Cheap; risky — a misbehaving experiment could affect production-bound traffic in theory (though distinct distributions). |

**Recommendation: B for daily use, A as the fallback when B isn't present.** Document the manual step to create B. The harness checks for B's presence by tag (`sg:lab:shared=1`) before each Tier-2 run; falls back to A if missing.

---

## Q5 — Public-resolver set: 6 or 8?

The existing `Route53__Public_Resolver__Checker.smart_verify_subset()` uses 6 (Cloudflare ×2, Google ×2, Quad9, AdGuard). The full set adds OpenDNS ×2. The lab experiments are mostly informational; cache-pollution risk is the same as the existing `--public-resolvers` mode in `sg aws dns records check`.

**Recommendation: experiments use the 6-resolver smart-verify subset by default; offer `--full-set` flag.** Match the existing convention.

---

## Q6 — Lambda function URL — auth-none vs auth-iam during experiments?

The lab Lambdas need to be invokable by the harness host + by CloudFront. Options:

| Opt | Position |
|-----|----------|
| **A** | **`auth_type='NONE'`** — Function URL is public. Anyone who discovers the URL can invoke. For a short-lived lab Lambda, low risk. |
| **B** | **`auth_type='AWS_IAM'`** — only IAM-signed requests work. CloudFront needs OAC; harness uses `boto3` to sign. More setup, harder for `curl` based experiments. |

**Recommendation: A for lab experiments only.** This is *not* the same decision as v2's production Function URL — that one gets a custom-origin-header verifier (review item #2). Lab Lambdas are torn down in <1 hour, so the risk is bounded.

---

## Q7 — Do experiments share resources across runs?

Some primitives (the wildcard ALIAS, the CF distribution) are expensive to create per-run. Two strategies:

| Opt | Position |
|-----|----------|
| **A** | **Per-run resources** — every experiment creates and tears down everything it touches. Pure but slow for CF/Lambda. |
| **B** | **Reusable lab fixtures** — `sg aws lab fixture create wildcard-cf` provisions a long-lived lab CF distribution once; subsequent experiments use it. Faster; reuse risk; another thing to manage. |

**Recommendation: A in phase P3; revisit B as a phase P-Followup once we know which fixtures hurt the most.** Premature reuse-optimisation makes the safety story harder.

---

## Q8 — Does the harness write into the repo or a sibling directory?

`.sg-lab/` in the repo root is the default. Alt: `~/.sg-lab/` (user-level). Alt: an env-var-defined path.

**Recommendation: repo-root by default (gitignored), env-var override (`SG_AWS__LAB__HOME`).** Repo-root keeps runs near the code they characterise; user-level loses the link.

---

## Q9 — Tests against real AWS in CI?

Integration tests under `tests/integration/` can run against AWS but cost money + need credentials. Options:

| Opt | Position |
|-----|----------|
| **A** | **Never in CI.** All AWS-touching tests gated by `SG_AWS__LAB__ALLOW_MUTATIONS=1` + `SG_AWS__LAB__DESTROY_TEST=1`. Run manually by Dev. |
| **B** | **Nightly in CI.** A separate workflow runs Tier-0 + Tier-1 daily, posts metrics. |
| **C** | **On-demand in CI.** A `workflow_dispatch` job lets Dev trigger experiments from the GitHub UI. |

**Recommendation: A initially; C for "run E11 from CI to check propagation against a known-good baseline" once we have a baseline.** Never B — daily CF distribution churn is overkill.

---

## Q10 — Do experiments take a `--repeat N` flag universally?

E10 / E11 / E30 naturally take repetition. Should every experiment? Risk: makes the surface fuzzy ("does --repeat make sense for E27? what does it even mean?").

**Recommendation: `--repeat` is per-experiment, opt-in.** Each experiment that supports it declares so in its metadata. Discoverable via `sg aws lab show <id>`.

---

## Q11 — What happens to lab resources if the operator's `aws-vault` session expires mid-run?

Boto3 will raise `ExpiredToken`. Layer 1 teardown will then fail; layer 2 signal handlers fire but also fail; layer 4 (TTL expiry) saves us.

**Recommendation: experiments should `boto3` with `boto3.session.Session()` cached on the harness; the session is refreshed if `aws-vault` is in use.** Document the failure mode in the README; the sweeper handles it.

---

## Q12 — Naming convention for lab resources?

Resources need prefixes that **operationally distinguish** them at-a-glance in the AWS console.

Recommendation, mirroring the codebase's `aws_name_for_stack` pattern:

| Resource | Pattern |
|----------|---------|
| R53 record | `lab-<experiment>-<run-id-short>.<zone>` — e.g. `lab-prop-a7b2c3.sg-compute.sgraph.ai` |
| Lambda | `sg-lab-<experiment>-<run-id-short>` — e.g. `sg-lab-cold-start-a7b2c3` |
| CF distribution | (no name — `Comment` field) `sg-lab e2e a7b2c3` |
| Security group | `sg-lab-<experiment>-<run-id-short>-sg` |
| EC2 instance | `sg-lab-<experiment>-<run-id-short>` (via Name tag) |
| ACM cert | `sg-lab-wildcard-<run-id-short>` (Domain `lab.<zone>` if Q1 = A; `<zone>` if B) |
| IAM role | `sg-lab-<experiment>-<run-id-short>-role` |
| SSM param | `/sg-compute/lab/<run-id>/<experiment>/<key>` |

The `<run-id-short>` is a 6-char nonce. The full run-id (ISO ts + nonce) lives in tags.

---

## Q13 — Should the harness reuse the `Vault_App__Service`'s naming machinery?

`Stack__Naming` provides `aws_name_for_stack`, `sg_name_for_stack` etc. Lab resources are NOT stacks; they're lab resources.

**Recommendation: separate `Lab__Naming` class in `sg aws lab service/`.** Use its own `lab_name_for_experiment(experiment, run_id)`. Don't conflate stacks with lab.

---

## Q14 — Should there be a `sg vault-publish lab` mounted as a sub-command?

Conceivably, vault-publish-specific lab work (e.g. "wake-cycle latency for slug X") could live under the vault-publish spec. But it sets up the wrong precedent — labs are *platform-level*, not spec-level.

**Recommendation: keep all lab experiments under `sg aws lab`.** A vault-publish-specific composite (E27) is fine; vault-publish itself doesn't mount its own lab tree.

---

## Q15 — How much human attention does Phase 0 (validate today's primitives) need?

The v2 brief's Phase 0 says "validate today's primitives manually" — but doesn't specify *what* to validate. The lab is the answer.

**Recommendation:** treat **Lab Phase P0 + P1 as the implementation of v2 Phase 0**. The v2 brief's Phase 0 becomes "run `sg aws lab run E01`, `E02`, `E03`, `E10`, `E11`, `E12` against the production zone; review the results; greenlight Phase 1a if numbers are within tolerance".

That gives Phase 0 a concrete, scriptable definition instead of a vague-instruction.

---

## When these are answered, the Dev contract is:

- The 8 module-files in [`05 §1`](05__module-layout.md#1-folder).
- The 24 experiment files in [`03`](03__experiment-catalogue.md).
- The three-layer safety story in [`04`](04__safety-and-cleanup.md).
- Tests under `tests/unit/sgraph_ai_service_playwright__cli/aws/lab/`.
- The phasing in [`07`](07__phasing.md) gives Dev a clear "ship P0+P1 first" instruction.

After P1 lands, this brief itself gets re-read alongside the **first batch of real numbers** from E10–E14 — that's the moment the v2 brief should be re-validated against measurement, not just architecture.
