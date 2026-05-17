---
title: "v0.2.29 — sg aws ec2 (Slice B)"
file: README.md
author: Architect (Claude)
date: 2026-05-17
status: PROPOSED — independent sibling pack of v0.2.29__sg-aws-primitives-expansion
size: M — ~1400 prod lines, ~600 test lines, ~2 calendar days
parent_umbrella: library/dev_packs/v0.2.29__sg-aws-primitives-expansion/
source_briefs:
  - team/humans/dinis_cruz/briefs/05/17/from__daily-briefs/v0.27.43__dev-brief__sg-compute-container-hosts-primitive.md
  - team/humans/dinis_cruz/briefs/05/17/from__daily-briefs/v0.27.43__dev-brief__instance-sizing-and-startup-experiments.md
feature_branch: claude/aws-primitives-support-uNnZY-ec2
---

# `sg aws ec2` — Slice B

**The EC2 primitive layer that the v0.2.30 container-hosts primitive will build on.** The two source briefs that drive this slice — [container-hosts](../../../team/humans/dinis_cruz/briefs/05/17/from__daily-briefs/v0.27.43__dev-brief__sg-compute-container-hosts-primitive.md) and [instance-sizing-experiments](../../../team/humans/dinis_cruz/briefs/05/17/from__daily-briefs/v0.27.43__dev-brief__instance-sizing-and-startup-experiments.md) — both want a clean, type-safe CLI for "list / describe / create / start / stop / terminate an EC2 instance" before their own substrate work can sit cleanly on top. Slice B delivers exactly that primitive layer. The container-hosts primitive itself and the measurement programme are explicit v0.2.30 work (per umbrella locked decisions #11 + #12).

Implementation mechanism: extract the genuinely-EC2-shaped logic from `scripts/provision_ec2.py` (~2500 LOC) and `Elastic__AWS__Client` into a tidy `aws/ec2/` namespace; `scripts/provision_ec2.py` keeps working as a thin Typer wrapper that delegates to the new primitives.

> **PROPOSED — does not exist yet.** Cross-check `team/roles/librarian/reality/cli/` (look for `cli/aws-*.md`) before describing anything here as built.

### Coexistence with existing `__cli/ec2/` (locked decision #14)

There is already a top-level package `sgraph_ai_service_playwright__cli/ec2/` (~550 LOC, `Ec2__AWS__Client` + `Ec2__Service` + schemas + primitives + AMI helpers). It powers:

- The FastAPI duality routes (`Routes__Ec2__Playwright` on `Fast_API__SP__CLI`)
- `default_playwright_image_uri()` / `default_sidecar_image_uri()` consumed by `Docker__Service`, `Firefox__Service`, and several specs
- `aws_account_id()` (now backed by the v0.2.28 credentials cache via `Sg__Aws__Session.account_id_from_context()`)

**Coexistence rule:** the new `aws/ec2/service/EC2__AWS__Client.py` *wraps and extends* the existing `__cli/ec2/service/Ec2__AWS__Client.py` — it does not reinvent it. Where the existing client already has a method that does what we need (`find_instances`, `instance_tag`, `resolve_target`), import and call it. Where new behaviour is needed (full `describe`, `pricing`, `ssh-info`, AMI alias resolution), add it in the new client. A v0.2.30 hygiene pack consolidates the two locations once the new CLI surface is stable.

This same coexistence principle applies whenever a slice finds a pre-existing top-level package (Slice H + `__cli/observability/` is the other example).

---

## Where this fits

This is **one of eight sibling slices** of the v0.2.29 milestone. The umbrella pack at [`v0.2.29__sg-aws-primitives-expansion/`](../v0.2.29__sg-aws-primitives-expansion/README.md) owns the locked decisions, the [Foundation brief](../v0.2.29__sg-aws-primitives-expansion/02__common-foundation.md), and the [orchestration plan](../v0.2.29__sg-aws-primitives-expansion/03__sonnet-orchestration-plan.md). **Read the umbrella first.**

This slice has no consumers among the other v0.2.29 slices. Its consumers are v0.2.30 packs (container-hosts primitive, instance-sizing measurement programme).

---

## Source briefs

Two briefs converge here:

- [`v0.27.43__dev-brief__sg-compute-container-hosts-primitive.md`](../../../team/humans/dinis_cruz/briefs/05/17/from__daily-briefs/v0.27.43__dev-brief__sg-compute-container-hosts-primitive.md) — the container-hosts primitive needs a clean EC2 primitive layer underneath
- [`v0.27.43__dev-brief__instance-sizing-and-startup-experiments.md`](../../../team/humans/dinis_cruz/briefs/05/17/from__daily-briefs/v0.27.43__dev-brief__instance-sizing-and-startup-experiments.md) — the measurement programme provisions/tears down instances across instance types

This slice ships the **primitive layer only**. The container-hosts primitive and the measurement programme are separate v0.2.30 packs.

---

## What you own

**Folder:** `sgraph_ai_service_playwright__cli/aws/ec2/` (Foundation ships the skeleton; you fill in the bodies)

### Verbs

| Verb | Tier | Notes |
|------|------|-------|
| `list` | read-only | All instances; `--state running|stopped|...`, `--tag K=V`, `--region`, `--json` |
| `describe <id-or-name>` | read-only | Full instance detail (state, type, networking, tags, attached volumes) |
| `ssh-info <id-or-name>` | read-only | Public DNS / public IP / username (per AMI); never the key — keys live in vault |
| `tags <id-or-name>` | read-only | Get/set/remove tags; `--add K=V`, `--remove K`, `--clear` (mutating verbs) |
| `instance-types` | read-only | List instance types available in the current region (cached) |
| `pricing <instance-type>` | read-only | Per-second / per-hour for the current region |
| `create` | mutating | Provision a new instance — see flags below |
| `start <id-or-name>` | mutating | Start a stopped instance |
| `stop <id-or-name>` | mutating | Stop a running instance (preserves EBS) |
| `terminate <id-or-name>` | mutating | Terminate (destroys volumes unless `--keep-volumes`) |
| `wait <id-or-name> --state <state>` | read-only | Block until instance reaches state (used by `create`) |

**Mutation gate:** `SG_AWS__EC2__ALLOW_MUTATIONS=1` required for `create / start / stop / terminate / tags --add|--remove|--clear`.

**`<id-or-name>` accepts a fuzzy match** on the instance's `Name` tag (single match required, ambiguity error otherwise) — same pattern as `Lambda__Name__Resolver`.

### `create` flags (the meaty verb)

```
sg aws ec2 create
  --name <logical-name>                      # required; becomes Name tag
  --instance-type <type>                     # required (or --instance-type-from-pool <pool-name>)
  --ami <id-or-alias>                        # alias resolves via Ami__Resolver (e.g. "ubuntu-22.04-arm64")
  --key-pair <name>                          # default: $SG_AWS__EC2__DEFAULT_KEY_PAIR
  --subnet <id>                              # default: $SG_AWS__EC2__DEFAULT_SUBNET
  --security-groups <id>[,<id>...]           # default: $SG_AWS__EC2__DEFAULT_SG
  --user-data <file>                         # cloud-init script
  --tags K=V[,K=V...]                        # in addition to the sg:* tags Foundation applies
  --wait                                     # block until running (default: true)
  --json
```

Honours CLAUDE.md rule #14 (no `sg-*` GroupName prefix; SG_NAME → `playwright-ec2-sg` style).

---

## Production files (indicative)

```
aws/ec2/
├── cli/
│   ├── Cli__EC2.py
│   └── verbs/
│       ├── Verb__EC2__List.py
│       ├── Verb__EC2__Describe.py
│       ├── Verb__EC2__SSH_Info.py
│       ├── Verb__EC2__Tags.py
│       ├── Verb__EC2__Instance_Types.py
│       ├── Verb__EC2__Pricing.py
│       ├── Verb__EC2__Create.py
│       ├── Verb__EC2__Start.py
│       ├── Verb__EC2__Stop.py
│       ├── Verb__EC2__Terminate.py
│       └── Verb__EC2__Wait.py
├── service/
│   ├── EC2__AWS__Client.py             # wraps Sg__Aws__Session
│   ├── EC2__Name__Resolver.py          # fuzzy match on Name tag
│   ├── EC2__Ami__Resolver.py           # alias → AMI ID (caches)
│   ├── EC2__Pricing__Client.py         # Pricing API (us-east-1 only — note the carve-out)
│   └── EC2__Instance__Wait.py          # polling wait with backoff
├── schemas/                            # Schema__EC2__Instance, ...Instance__Type, ...Pricing, ...Create__Request, etc.
├── enums/                              # Enum__EC2__State, Enum__EC2__Architecture
├── primitives/                         # Safe_Str__EC2__Instance_Id, Safe_Str__EC2__AMI_Id, Safe_Str__EC2__SG_Id, etc.
└── collections/                        # List__Schema__EC2__Instance, Dict__EC2__Tag
```

### Existing code to migrate (in this slice's PR, **not** a separate cleanup)

- `scripts/provision_ec2.py` — refactor to a thin wrapper that calls `sg aws ec2 create` with the right flags. Keep the script entry-point working; just delegate the boto3 work to the new primitives.
- `sgraph_ai_service_playwright__cli/elastic/service/Elastic__AWS__Client.py` — extract the genuinely EC2-shaped helpers (security-group naming, name resolution) into `aws/ec2/service/`. Leave the Elastic-specific orchestration in `elastic/`; it now calls the new `aws/ec2/` primitives.

---

## What you do NOT touch

- Any other surface folder under `aws/`
- `aws/_shared/` (Foundation-owned)
- The container-hosts primitive — separate v0.2.30 pack
- The instance-sizing measurement programme — separate v0.2.30 pack
- Direct boto3 — `EC2__AWS__Client` wraps `Sg__Aws__Session` via `osbot-aws`

---

## Acceptance

```bash
# read-only
sg aws ec2 list                                                        # → table or --json
sg aws ec2 list --state running --tag sg:owner=$USER
sg aws ec2 describe <known-instance>                                   # → detail panel
sg aws ec2 ssh-info <known-instance>
sg aws ec2 instance-types --json | jq length
sg aws ec2 pricing t4g.nano                                            # → per-second + per-hour

# mutating
SG_AWS__EC2__ALLOW_MUTATIONS=1 sg aws ec2 create \
    --name sg-test-tmp-$(date +%s) --instance-type t4g.nano \
    --ami ubuntu-22.04-arm64 --yes
# (the above must be wait-by-default, end with the instance running, and the sg:* tags present)

sg aws ec2 list --tag sg:owner=$USER --json | jq '.[].instance_id'

SG_AWS__EC2__ALLOW_MUTATIONS=1 sg aws ec2 stop sg-test-tmp-<suffix> --yes
SG_AWS__EC2__ALLOW_MUTATIONS=1 sg aws ec2 start sg-test-tmp-<suffix> --yes
SG_AWS__EC2__ALLOW_MUTATIONS=1 sg aws ec2 terminate sg-test-tmp-<suffix> --yes

# regression: scripts/provision_ec2.py still works (calls the new primitives)
python scripts/provision_ec2.py --help

# tests
pytest tests/unit/sgraph_ai_service_playwright__cli/aws/ec2/ -v
SG_AWS__EC2__INTEGRATION=1 pytest tests/integration/sgraph_ai_service_playwright__cli/aws/ec2/ -v
```

---

## Deliverables

1. All files under `aws/ec2/` per the layout above
2. Refactored `scripts/provision_ec2.py` + extracted helpers from `elastic/` (existing tests must keep passing)
3. Unit tests under `tests/unit/sgraph_ai_service_playwright__cli/aws/ec2/`
4. Integration tests under `tests/integration/sgraph_ai_service_playwright__cli/aws/ec2/` (gated)
5. New user-guide page `library/docs/cli/sg-aws/10__ec2.md`
6. One row added to `library/docs/cli/sg-aws/README.md` "at-a-glance command map"
7. Reality-doc update: new `team/roles/librarian/reality/cli/aws-ec2.md` (the existing `cli/ec2.md` continues to cover the FastAPI duality) (supersedes the `scripts/provision_ec2.py` note)

---

## Risks to watch

- **Security-group naming.** CLAUDE.md rule #14 forbids `sg-*` GroupName. Use the existing helper from `Elastic__AWS__Client` (`sg_name_for_stack`) — promote it to `aws/ec2/service/`.
- **AMI alias drift.** Aliases like `ubuntu-22.04-arm64` resolve to different IDs per region and over time. Cache resolutions for the session; expose `--ami-id` to bypass alias resolution.
- **Wait-for-state semantics.** Default `--wait` to true on `create / start / stop / terminate`. Polling backoff: 2s → 5s → 10s → 15s capped, total 5 min. `Ec2__Service` (in the existing `__cli/ec2/`) already has wait logic — promote/reuse, do not reinvent.
- **Named-resource → verb pattern.** EC2 `<id-or-name>` resolution + per-instance verbs should follow the existing `Lambda__Click__Group` two-level dynamic Click group at `sgraph_ai_service_playwright__cli/aws/lambda_/cli/Lambda__Click__Group.py` so REPL prefix navigation works (`sg-c stop` style). The pattern is small enough to copy; do NOT extract a shared base.
- **Pricing API region.** AWS Pricing API only lives in `us-east-1` regardless of caller region. `EC2__Pricing__Client` ignores the resolver and pins us-east-1.
- **Existing script regression.** `scripts/provision_ec2.py` callers (CI, partner provisioning, etc.) must keep working. Migrate behaviour, not interface.
- **Name-tag fuzzy resolution.** Ambiguity (two instances both named `dev-*`) must error with both IDs listed, not pick one silently.

---

## Commit + PR

Branch: `claude/aws-primitives-support-uNnZY-ec2`

Commit message: `feat(v0.2.29): sg aws ec2 — primitives, name resolver, promotes provision_ec2.py`.

PR target: `claude/aws-primitives-support-uNnZY`. Tag the Opus coordinator. Do **not** merge yourself.

---

## Cancellation / descope

Independent of every other v0.2.29 slice. Cancelling here just defers v0.2.30 container-hosts and instance-sizing programmes; nothing else in v0.2.29 changes.
