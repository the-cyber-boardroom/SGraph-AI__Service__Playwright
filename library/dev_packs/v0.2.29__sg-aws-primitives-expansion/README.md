---
title: "sg aws primitives expansion — Umbrella Pack"
file: README.md
author: Architect (Claude)
date: 2026-05-17
repo: SGraph-AI__Service__Playwright @ dev (v0.2.27 line → targeting v0.2.29)
status: PROPOSED — no code yet. For human ratification before Dev picks up.
parent:
  - team/humans/dinis_cruz/briefs/05/17/from__daily-briefs/
related:
  - library/docs/cli/sg-aws/                                       # user-facing surface that exists today (v0.2.26)
  - library/dev_packs/v0.2.28__sg-aws-credentials/                 # v0.2.28 mirror pack — same shape as this milestone
  - sgraph_ai_service_playwright__cli/credentials/                 # Sg__Aws__Session (the shared client seam)
  - sgraph_ai_service_playwright__cli/ec2/                         # existing top-level ec2 pkg (FastAPI duality) — Slice B coexists with it
  - sgraph_ai_service_playwright__cli/observability/               # existing top-level observability pkg (AMP/OS/AMG infra) — Slice H is the read surface beside it
  - team/roles/librarian/reality/cli/                              # canonical reality-doc home for the new sg aws X surfaces (cli/aws-{s3,ec2,...}.md)
feature_branch: claude/aws-primitives-support-uNnZY
---

# `sg aws` primitives expansion — Umbrella Pack

A coordinated expansion of the `sg aws *` command surface to absorb **eight more AWS surfaces** into the type-safe SG/Compute treatment: S3, EC2, Fargate, IAM-graph, Bedrock (chat + agent + tool), CloudTrail, scoped credential delivery, and a unified observability v1 REPL.

This is the **umbrella pack**. It owns three things only:

1. **Locked decisions** that apply across every slice.
2. **The Foundation brief** (Agent 0) — the shared scaffold that must land before any sibling pack starts.
3. **The orchestration plan** — how the 8 sibling packs fire in parallel after Foundation merges.

> **PROPOSED — does not exist yet.** Every new `sg aws X` namespace below is **PROPOSED**. Cross-check against [`team/roles/librarian/reality/`](../../../team/roles/librarian/reality/README.md) before describing anything here as built.

---

## How this pack relates to the sibling packs

This pack does **not** contain per-slice implementation briefs. Each slice lives in its own sibling pack under `library/dev_packs/` so it can be **reviewed, approved, scheduled, and executed independently** of the others.

```
library/dev_packs/
├── v0.2.29__sg-aws-primitives-expansion/   ← YOU ARE HERE — umbrella (locked decisions + Foundation + orchestration)
├── v0.2.29__sg-aws-s3/                     ← Slice A — independent pack
├── v0.2.29__sg-aws-ec2/                    ← Slice B — independent pack
├── v0.2.29__sg-aws-fargate/                ← Slice C — independent pack
├── v0.2.29__sg-aws-iam-graph/              ← Slice D — independent pack
├── v0.2.29__sg-aws-bedrock/                ← Slice E — independent pack
├── v0.2.29__sg-aws-cloudtrail/             ← Slice F — independent pack
├── v0.2.29__sg-aws-scoped-creds/           ← Slice G — independent pack
└── v0.2.29__sg-aws-observability/          ← Slice H — independent pack
```

Each sibling pack:

- Has its own `README.md` (the brief the Sonnet sub-agent receives — self-contained)
- Has its own acceptance commands
- Has its own size/effort estimate
- Has its own user-guide page deliverable (one new file under `library/docs/cli/sg-aws/`)
- Can be **cancelled, descoped, or re-ordered** without touching the others
- Points back here for the foundation + locked decisions + orchestration plan only

---

## One-paragraph summary

The 10 AWS-related briefs filed on 2026-05-15 (`team/humans/dinis_cruz/briefs/05/17/from__daily-briefs/`) all point in the same direction: **make every AWS surface we touch first-class in the `sg aws` CLI, with type-safe schemas, vault-grounded outputs, and `Sg__Aws__Session`-mediated credentials**. This umbrella carves that work into a Foundation PR (new namespace stubs, shared mutation-gate convention, shared tagging convention, shared `Schema__AWS__*` primitives, shared observability source contract) and **eight parallel sibling packs** — one per AWS surface. Each sibling owns its own folder under `sgraph_ai_service_playwright__cli/aws/`, its own per-namespace mutation-gate env var, its own Click sub-tree under the locked top-level shape, and its own acceptance commands. The only shared file at integration time is the namespace registration in `Cli__Aws.py`, which is append-only and trivial to rebase.

---

## Source briefs

This umbrella synthesises the 10-file daily brief drop from 2026-05-15:

| Source brief | Drives sibling pack |
|--------------|---------------------|
| [`v0.27.43__dev-brief__s3-native-cli-support.md`](../../../team/humans/dinis_cruz/briefs/05/17/from__daily-briefs/v0.27.43__dev-brief__s3-native-cli-support.md) | `v0.2.29__sg-aws-s3/` |
| [`v0.27.43__dev-brief__sg-compute-container-hosts-primitive.md`](../../../team/humans/dinis_cruz/briefs/05/17/from__daily-briefs/v0.27.43__dev-brief__sg-compute-container-hosts-primitive.md) | `v0.2.29__sg-aws-ec2/` — primitive layer; the container-host primitive itself is a separate pack |
| [`v0.27.43__dev-brief__instance-sizing-and-startup-experiments.md`](../../../team/humans/dinis_cruz/briefs/05/17/from__daily-briefs/v0.27.43__dev-brief__instance-sizing-and-startup-experiments.md) | `v0.2.29__sg-aws-ec2/` — provides the primitives the measurement programme will use |
| [`v0.27.43__dev-brief__fargate-vault-hosting-experiment.md`](../../../team/humans/dinis_cruz/briefs/05/17/from__daily-briefs/v0.27.43__dev-brief__fargate-vault-hosting-experiment.md) | `v0.2.29__sg-aws-fargate/` |
| [`v0.27.43__dev-brief__iam-graph-visualisation-and-lockdown.md`](../../../team/humans/dinis_cruz/briefs/05/17/from__daily-briefs/v0.27.43__dev-brief__iam-graph-visualisation-and-lockdown.md) | `v0.2.29__sg-aws-iam-graph/` — discovery + cleanup workflow only; CloudTrail-evidence layer deferred |
| [`v0.27.43__planning-brief__bedrock-cli-native-support.md`](../../../team/humans/dinis_cruz/briefs/05/17/from__daily-briefs/v0.27.43__planning-brief__bedrock-cli-native-support.md) | `v0.2.29__sg-aws-bedrock/` — chat + agent + tool only; kb/guardrail/eval/observe deferred |
| (derived from IAM + observability briefs) | `v0.2.29__sg-aws-cloudtrail/` |
| [`v0.27.43__arch-brief__dynamic-credential-delivery-service.md`](../../../team/humans/dinis_cruz/briefs/05/17/from__daily-briefs/v0.27.43__arch-brief__dynamic-credential-delivery-service.md) | `v0.2.29__sg-aws-scoped-creds/` — local Phase 1+2 only |
| [`v0.27.43__arch-brief__unified-observability-session.md`](../../../team/humans/dinis_cruz/briefs/05/17/from__daily-briefs/v0.27.43__arch-brief__unified-observability-session.md) | `v0.2.29__sg-aws-observability/` |
| [`v0.27.43__addendum__s3-and-observability-additional-context.md`](../../../team/humans/dinis_cruz/briefs/05/17/from__daily-briefs/v0.27.43__addendum__s3-and-observability-additional-context.md) | `v0.2.29__sg-aws-s3/` + `v0.2.29__sg-aws-observability/` |
| [`v0.27.43__strategy-brief__serverless-sg-workflows-beyond-lambda.md`](../../../team/humans/dinis_cruz/briefs/05/17/from__daily-briefs/v0.27.43__strategy-brief__serverless-sg-workflows-beyond-lambda.md) | Strategic framing (not implemented directly) |

Source briefs are the ground truth. Where this umbrella restates them it is for Dev convenience; if it contradicts them it is a bug — open an Architect-review request.

---

## Umbrella file index

| # | File | Purpose |
|---|------|---------|
| 00 | this README | Status, summary, locked decisions, surface map, sign-off |
| 01 | [`01__scope-and-architecture.md`](01__scope-and-architecture.md) | What's in, what's out, the surface map, where it slots into the reality doc |
| 02 | [`02__common-foundation.md`](02__common-foundation.md) | **Agent 0 brief** — the shared scaffold (must land first) |
| 03 | [`03__sonnet-orchestration-plan.md`](03__sonnet-orchestration-plan.md) | How the 8 sibling packs fire in parallel after Foundation merges |

---

## Sibling pack index

| # | Sibling pack | Size | Effort | Description |
|---|--------------|-----:|-------:|-------------|
| A | [`v0.2.29__sg-aws-s3/`](../v0.2.29__sg-aws-s3/README.md) | M-L | ~3 d | `sg aws s3` — 16+ verbs incl. vim integration and format-aware rendering |
| B | [`v0.2.29__sg-aws-ec2/`](../v0.2.29__sg-aws-ec2/README.md) | M | ~2 d | `sg aws ec2` — promotes `scripts/provision_ec2.py` to first-class CLI |
| C | [`v0.2.29__sg-aws-fargate/`](../v0.2.29__sg-aws-fargate/README.md) | M | ~2.5 d | `sg aws fargate` — clusters, task definitions, tasks, logs |
| D | [`v0.2.29__sg-aws-iam-graph/`](../v0.2.29__sg-aws-iam-graph/README.md) | L | ~3 d | `sg aws iam graph` — discovery + cleanup workflow |
| E | [`v0.2.29__sg-aws-bedrock/`](../v0.2.29__sg-aws-bedrock/README.md) | XL | ~4 d | `sg aws bedrock` — chat + agent + tool sub-trees |
| F | [`v0.2.29__sg-aws-cloudtrail/`](../v0.2.29__sg-aws-cloudtrail/README.md) | S | ~1.5 d | `sg aws cloudtrail` — read-only events + trails |
| G | [`v0.2.29__sg-aws-scoped-creds/`](../v0.2.29__sg-aws-scoped-creds/README.md) | M | ~2.5 d | `sg aws creds` — local scoped STS AssumeRole delivery |
| H | [`v0.2.29__sg-aws-observability/`](../v0.2.29__sg-aws-observability/README.md) | M | ~3 d | `sg aws observe` — unified observability v1 REPL |

**Total: ~14.8 K prod lines + ~5.9 K test lines. Sequential ≈ 22 days. Parallelised after Foundation ≈ 5 calendar days.**

---

## Locked decisions

These are settled. If any seems wrong, raise an Architect-review request — do not silently change them.

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | **Eight new top-level Click groups under `sg aws`**: `s3`, `ec2`, `fargate`, `bedrock`, `cloudtrail`, `creds`, `observe` (new); `iam graph` (sub-tree under existing `iam`). Each is a new folder under `sgraph_ai_service_playwright__cli/aws/` (or extension of an existing one), mirroring the established `aws/dns/` shape (`cli/ / service/ / schemas/ / enums/ / primitives/ / collections/`). | "Same shape as everything else." One layer per concern. |
| 2 | **Per-namespace mutation-gate env var.** Each new mutating surface gets its own gate, matching the existing convention (see [`library/docs/cli/sg-aws/01__getting-started.md`](../../docs/cli/sg-aws/01__getting-started.md)): `SG_AWS__S3__ALLOW_MUTATIONS`, `SG_AWS__EC2__ALLOW_MUTATIONS`, `SG_AWS__FARGATE__ALLOW_MUTATIONS`, `SG_AWS__BEDROCK__ALLOW_MUTATIONS` (for AgentCore/agent/tool mutations only — `chat` is read-only), `SG_AWS__IAM__ALLOW_MUTATIONS` (existing — extends to `iam graph delete`), `SG_AWS__CREDS__ALLOW_MUTATIONS` (for scope catalogue edits). CloudTrail and observability are read-only — no gate. | Consistent safety pattern; one gate per slice means slices don't fight over gate semantics. |
| 3 | **Every AWS call routes through `osbot-aws` or an existing/new `*__AWS__Client` class that wraps `Sg__Aws__Session`.** No direct boto3. The narrow exceptions documented in CLAUDE.md rule #14 stand; no new ones. | CLAUDE.md rule #14. The v0.2.28 credentials migration made `Sg__Aws__Session` the single client seam — every new client honours it from day one. |
| 4 | **Type_Safe everywhere, no Pydantic, no Literals, one class per file, empty `__init__.py`, no re-exports.** | CLAUDE.md rules #1, #3, #20, #21, #22. |
| 5 | **Bedrock scope (Slice E) is `chat` + `agent` + `tool` ONLY.** `kb`, `guardrail`, `eval`, `observe`, `meta`, `multi-agent collaboration`, `payments` are explicitly deferred to a v0.2.30 follow-up pack. The chat sub-command ships first; `agent` + `tool` ship in the same PR but behind separate verb trees. | Planning brief is large and has open design decisions on vault-grounding schema, model-ID resolution, and AgentCore SDK choice. Bound the slice. |
| 6 | **IAM graph scope (Slice D) is Phase 1 + Phase 3 ONLY.** Phase 4 (CloudTrail-evidence recommendations) depends on Slice F. Phases 5-6 (expansion workflow + SG command migration to scoped roles) ship in v0.2.30 once Slice G's scope catalogue has stabilised. | Avoids cross-slice dependency at implementation time. |
| 7 | **Scoped credentials (Slice G) is local-only — Phase 1 + Phase 2.** Phase 5 (deployed credential service) and Phase 6 (audit dashboard) are out of scope. The local service config and scope catalogue both live in a vault per the brief's vault-grounding rule. | Validates the pattern with low risk. Network/deployment complexity comes once the local pattern works. |
| 8 | **Observability v1 (Slice H) ships three sources: S3 (via Slice A), CloudWatch Logs (existing `aws/logs/`), CloudTrail (via Slice F).** CloudFront-via-Firehose is a configured S3 prefix, not a separate source. AWS dashboard screenshots are v2. Product analytics layer is v2. Customer-facing reporting is v2. | Substrate first; the layers on top come once the substrate is solid (addendum §4). |
| 9 | **Per-slice branches off `claude/aws-primitives-support-uNnZY`** (this is the existing feature branch). Each sibling pack opens its own PR to the integration branch; integration branch merges to `dev` once all eight are reviewed. The Opus coordinator runs the integration acceptance suite before opening the integration→dev PR. | Mirrors v0.2.28. Keeps blast radius bounded; allows reviews in parallel. |
| 10 | **No vault-aware S3 wrappers (`s3 vault-open/sync/diff/ls`) in this milestone.** Those depend on the Vault Synchronizer Tool (13 May brief) and ship together in a v0.2.30 vault-S3 pack. | Out of scope. |
| 11 | **No container hosts primitive (`sg-compute container-host/container`) in this milestone.** That's its own substrate work that uses the EC2 primitive Slice B delivers. Separate v0.2.30 pack. | Distinct workstream. |
| 12 | **No instance-sizing measurement programme in this milestone.** That's a measurement programme built on top of the EC2 primitive Slice B delivers. Separate v0.2.30 pack. | Distinct workstream. |
| 13 | **`sg credentials` re-mounts under `sg aws credentials` in the Foundation PR.** The existing top-level `sg credentials` mount stays as a **hidden alias** (no `--help` exposure) for one release; v0.2.30 drops the alias. This makes the v0.2.28 store reachable from the same namespace tree as Slice G's `sg aws creds` (scoped/temporary) so the user-guide `08__credentials.md` matches the actual command surface. | Resolves the `sg credentials` vs `sg aws credentials` vs `sg aws creds` naming confusion called out in the architect review (2026-05-17 §1.3). |
| 14 | **Slice B (EC2) coexists with the existing top-level `__cli/ec2/` package.** That package powers the FastAPI duality (`Routes__Ec2__Playwright` on `Fast_API__SP__CLI`), supplies `default_playwright_image_uri()` / `default_sidecar_image_uri()` to Docker/Firefox specs, and owns the existing `Ec2__AWS__Client`. The new `__cli/aws/ec2/` **imports** `Ec2__AWS__Client` from the existing location rather than reinventing it. A v0.2.30 hygiene pack consolidates the two locations. Same coexistence rule applies if any other slice finds a pre-existing top-level package (e.g. Slice H vs `__cli/observability/` — different semantics, both stay). | Smallest blast radius; matches the precedent set by `aws/cf/` coexisting with `sg_compute_specs/vault_publish/`'s CF helpers. See architect review §1.1 + §1.2. |

---

## Surface map at a glance

```
sg aws
├── (existing) acm / billing / cf / credentials / dns / iam / lambda / logs
│
├── s3            ← Slice A (NEW)
├── ec2           ← Slice B (NEW — promotes scripts/provision_ec2.py + Elastic CLI)
├── fargate       ← Slice C (NEW)
├── iam graph     ← Slice D (NEW sub-tree under existing iam)
├── bedrock       ← Slice E (NEW — chat + agent + tool)
│     ├── chat {claude,nova,llama,openai,any,list-models}
│     ├── agent {create,invoke,list,stop,memory,tools}
│     └── tool {browser,code-interpreter}
├── cloudtrail    ← Slice F (NEW — read-only)
├── creds         ← Slice G (NEW — local scoped credential delivery)
└── observe       ← Slice H (NEW — unified observability REPL)
```

`Cli__Aws.py` (top-level `sg aws` group) gains **seven new group registrations** in the Foundation PR; the eighth (`iam graph`) is a sub-group on the existing `iam` Click group, also wired by Foundation.

---

## Critical-path sign-off (Architect → Dev)

Before any sibling pack picks up its slice:

- [ ] All 14 locked decisions accepted by Dinis
- [ ] Foundation `02__common-foundation.md` reviewed by Dev — confirms it can be one PR
- [ ] `03__sonnet-orchestration-plan.md` reviewed — sibling pack boundaries are independent
- [ ] Feature branch `claude/aws-primitives-support-uNnZY` is current with `dev`
- [ ] AppSec has reviewed the scoped-credentials threat model (`v0.2.29__sg-aws-scoped-creds/`)
- [ ] An owner for the **scope catalogue vault** has been named (Slice G needs this before it can ship Phase 2)
- [ ] An owner for the **default Bedrock region + model-ID alias table** has been named (Slice E needs this before `chat` ships)

---

## Companion: user-guide update

This milestone also includes a small update to the user-facing pack [`library/docs/cli/sg-aws/`](../../docs/cli/sg-aws/) — a new `08__credentials.md` page covering the `sg aws credentials` verbs that landed in v0.2.28 (Phase B/C/D). The eight new namespaces from this milestone each get their own user-guide page (`09__s3.md` through `16__observe.md`) when their sibling slice merges. Per-sibling-pack briefs include the user-doc page as a deliverable so the user-facing surface stays in lock-step with the implementation.
