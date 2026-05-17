---
title: "Bedrock Chat — Setup, Check, and Onboarding UX"
file: 02__chat-ux-and-setup.md
author: Architect (Claude — Opus 4.7)
date: 2026-05-17
parent_pack: library/dev_packs/v0.2.29__sg-aws-bedrock/README.md
status: PROPOSED — improvement brief for Slice E follow-up
trigger: |
  User ran `sg aws bedrock chat list-models` in eu-west-2 and got
  "0 models" with no indication whether the cause was IAM permissions,
  region not supported, no model access enabled, or genuinely zero models.
audience: Sonnet sub-agent extending Slice E
size: M — ~400 prod LOC + ~150 test LOC, ~3-4 hours
---

# Bedrock chat — setup, check, and onboarding UX

## The problem (one paragraph)

`sg aws bedrock chat list-models` swallows every exception (`try: ... except Exception: return models` in `Bedrock__Control__AWS__Client.list_models`) and returns an empty list. A user with no IAM permission, no Bedrock regional support, no enabled model access, or a wrong region all see the same `0 models` table. There's no path forward; the user has to guess what's wrong, hit AWS docs, find the Bedrock console, navigate "Manage model access", figure out the IAM policy snippet, and then come back to the CLI. **The CLI knows what's wrong (the exception carries it) and should say so.**

## What to build

Two new verbs on `sg aws bedrock`, plus a fix to `list-models`:

### 1. `sg aws bedrock check` — diagnostic preflight

Modelled on `sg doctor preflight`. Runs ~8 checks against the active sg role + region, prints a Rich table with ✓ / ✗ / ⚠, and exits non-zero on any failure. No mutations; safe to run repeatedly.

| # | Check | Pass | Fail message |
|---|-------|------|--------------|
| 1 | Active sg role resolves to STS identity | `dev → arn:aws:iam::123:user/dinis` | Caller-identity failed: `<exception message>` — likely no AWS credentials in the shell. Run `eval $(sg credentials switch <role>)`. |
| 2 | Region supports Bedrock | `eu-west-2 ✓` (from a curated allowlist of regions where Bedrock is GA) | Region `eu-west-2` does not host Bedrock as of v0.2.29. Supported: `us-east-1, us-west-2, eu-west-3, …`. Pick one with `--region` or activate a role whose default region is supported. |
| 3 | IAM permission `bedrock:ListFoundationModels` | Yes | Permission denied. Required IAM action: `bedrock:ListFoundationModels`. Run `sg aws bedrock setup --print-policy` for the minimal policy JSON. |
| 4 | Total models in catalogue (regardless of access) | `42 models in eu-west-2` | (only fires if check 3 passed) |
| 5 | Models with enabled access | `8 of 42 enabled` | `0 of 42 enabled — visit https://eu-west-2.console.aws.amazon.com/bedrock/home?region=eu-west-2#/modelaccess to enable model access. Or run` `sg aws bedrock setup --open-console`. |
| 6 | At least one Claude / Nova / Llama model enabled (per provider used by Slice E) | `claude: 3, nova: 2, llama: 1` | `claude: 0 enabled` — `chat claude` will fail. Enable a Claude model first. |
| 7 | IAM permission `bedrock:InvokeModel` (smoke-test a 1-token call against the cheapest enabled model) | `invoke OK — claude-haiku, 1 token, $0.0000004` | InvokeModel denied. Required IAM action: `bedrock:InvokeModel` (resource scoped to the model ARN). |
| 8 | Capture writer reachable | `~/.sg/aws/bedrock/ — writable, 0600 enforced` | `~/.sg/aws/bedrock/ — cannot create (Permission denied). Set $SG_AWS__BEDROCK__CAPTURE_ROOT or check perms.` |

Output shape (the existing Rich-panel style we already use for `sg doctor preflight`):

```
$ sg aws bedrock check
  Bedrock preflight  ·  role=dev  ·  region=eu-west-2

  [✓]  sts identity         arn:aws:iam::123456789012:user/dinis
  [✓]  region supported     eu-west-2 (Bedrock GA)
  [✓]  list-models perm     bedrock:ListFoundationModels
  [✓]  models in catalogue  42
  [⚠]  models with access   0 of 42 — none enabled yet
  [✗]  claude available     0 enabled — `chat claude` will fail
  [✗]  invoke perm          smoke-test skipped (no models enabled)
  [✓]  capture writer       ~/.sg/aws/bedrock/ writable

  Next step:  sg aws bedrock setup --open-console
                (opens https://eu-west-2.console.aws.amazon.com/bedrock/home#/modelaccess)
              Or run:  sg aws bedrock setup --print-policy   # IAM policy JSON
```

Exit code: 0 if all green; 1 if any check is ✗; 0 with stderr warning if only ⚠ (warning, not blocking).

### 2. `sg aws bedrock setup` — guided enablement

Read-only by default; only mutates if the user explicitly opts in. Two modes:

#### Mode A — print-and-open (default for v0.2.29 — no AWS mutations)

```
$ sg aws bedrock setup
  Bedrock setup  ·  role=dev  ·  region=eu-west-2

  Step 1 of 3  ·  IAM permissions
    The active role needs these actions to use sg aws bedrock chat:
      bedrock:ListFoundationModels
      bedrock:GetFoundationModel
      bedrock:InvokeModel
      bedrock:InvokeModelWithResponseStream         (for --stream)

    Minimal policy JSON (copy or pipe into `sg aws iam role attach-policy`):
      {
        "Version": "2012-10-17",
        "Statement": [{
          "Sid": "SgAwsBedrockChat",
          "Effect": "Allow",
          "Action": [
            "bedrock:ListFoundationModels",
            "bedrock:GetFoundationModel",
            "bedrock:InvokeModel",
            "bedrock:InvokeModelWithResponseStream"
          ],
          "Resource": "*"
        }]
      }

    To attach to your active role automatically (PROPOSED — requires
    Slice G scoped-creds; for now, do it via the AWS Console or aws-cli):
      aws iam put-role-policy \
        --role-name <your-role> \
        --policy-name SgAwsBedrockChat \
        --policy-document file://<saved-snippet>.json

  Step 2 of 3  ·  Model access
    Bedrock requires explicit sign-up for each foundation model.

    For Slice E's chat commands, enable at least:
      Anthropic Claude Haiku   (cheap; recommended default)
      Amazon Nova Micro        (cheap; non-Anthropic option)

    Console deeplink:
      https://eu-west-2.console.aws.amazon.com/bedrock/home?region=eu-west-2#/modelaccess

    Click "Manage model access" → select the models above → submit.
    Approval is typically instant; some Anthropic models require a one-time
    use-case justification.

  Step 3 of 3  ·  Verify
    After completing steps 1 and 2:
      sg aws bedrock check                  # all green
      sg aws bedrock chat claude --prompt "say ok"
```

Flags:

| Flag | Behaviour |
|------|-----------|
| `--open-console` | Open the model-access deeplink in `$BROWSER` (using `webbrowser.open`); fall back to printing the URL |
| `--print-policy [--output FILE]` | Print the IAM policy JSON to stdout (or write to FILE) — pipeable into `aws iam put-role-policy --policy-document file://-` |
| `--region <R>` | Override active role's region |
| `--models claude,nova,llama` | Tailor the model-access recommendations to providers the user cares about (default: `claude,nova` — Slice E's primary chat backends) |

#### Mode B — auto-setup (PROPOSED — defer to v0.2.30, depends on Slice G)

```
$ SG_AWS__BEDROCK__ALLOW_MUTATIONS=1 sg aws bedrock setup --apply
  → Calls sg aws iam role create-policy with the JSON above
  → Calls sg aws iam role attach-policy
  → Cannot enable model access programmatically (AWS console is the only path)
  → Prints "Step 2 still requires the console"
```

This is out of scope for the v0.2.29 commit. The brief includes it so the verb tree we ship is forward-compatible (the `--apply` flag works only behind the mutation gate; without `--apply`, it's all print-and-open).

### 3. Fix `Bedrock__Control__AWS__Client.list_models` — stop swallowing exceptions

Today:

```python
def list_models(self, region: str = None, provider_filter: str = None) -> List__Schema__Bedrock__Model:
    effective_region = region or self.current_region()
    bedrock          = self.client(effective_region)
    models           = List__Schema__Bedrock__Model()
    try:
        kwargs = {'byInferenceType': 'ON_DEMAND'}
        if provider_filter:
            kwargs['byProvider'] = provider_filter
        resp  = bedrock.list_foundation_models(**kwargs)
        items = resp.get('modelSummaries', [])
    except Exception:
        return models                                  # ← silent miss; user sees "0 models"
    ...
```

The `except Exception: return models` is the user's whole problem. Three options:

- **(A)** Propagate the exception; `Cli__Bedrock.list_models` catches `botocore.exceptions.ClientError` and renders a hint via `console.print(...)` then `raise typer.Exit(1)`. (Matches the M-1 fix shape from my Slice B review.)
- **(B)** Return a `Schema__Bedrock__List_Models__Result` (typed) that carries either `models` or `error_code + error_message + hint`. The CLI renders the hint.
- **(C)** Best of both: propagate by default, but `Cli__Bedrock.check` catches and renders the diagnostic.

I recommend **(A)** for `list_models` itself (consistent with M-1) plus **(C)** for the `check` verb (catches at the verb boundary, renders a row in the diagnostic table).

The hint table the verb prints when AccessDenied:

```
$ sg aws bedrock chat list-models
  [✗] Permission denied: bedrock:ListFoundationModels
      The active role does not have this permission.
      Run:  sg aws bedrock check
      Or:   sg aws bedrock setup --print-policy
```

---

## What this enables (the workflow)

```
$ sg credentials switch dev
$ sg aws bedrock check
  [✗] claude available — 0 enabled
$ sg aws bedrock setup --open-console
  (opens Bedrock console at the model-access page)
  → user clicks, enables Claude Haiku, submits
$ sg aws bedrock check
  [✓] claude available — 1 enabled
$ sg aws bedrock chat claude --prompt "say ok"
  ok
```

Three commands from "I don't know what's wrong" to "working chat call". Today it's an arbitrary AWS-docs trawl.

---

## Production files (indicative)

```
aws/bedrock/
├── cli/
│   ├── Cli__Bedrock.py                      ← add `check` + `setup` to the top-level group
│   └── verbs/
│       ├── verb_check.py                    ← new
│       └── verb_setup.py                    ← new
├── service/
│   ├── Bedrock__Preflight.py                ← new — orchestrates the 8 checks
│   ├── Bedrock__Setup__Renderer.py          ← new — renders the IAM JSON + console deeplinks
│   ├── Bedrock__Region__Catalogue.py        ← new — curated list of Bedrock-supported regions
│   └── (existing) Bedrock__Control__AWS__Client.py  ← amend: stop swallowing the exception
└── schemas/
    ├── Schema__Bedrock__Check__Result.py    ← new — { check_name, status, message, hint }
    └── Schema__Bedrock__Setup__Step.py      ← new — { step_no, title, body, deeplink }
```

Plus collections (`List__Schema__Bedrock__Check__Result`, `List__Schema__Bedrock__Setup__Step`) and one enum (`Enum__Bedrock__Check__Status` — `PASS / WARN / FAIL`).

---

## Tests

```
tests/unit/sgraph_ai_service_playwright__cli/aws/bedrock/
├── service/
│   ├── test_Bedrock__Preflight.py             ← 8 tests, one per check (all use in-memory clients)
│   ├── test_Bedrock__Region__Catalogue.py     ← supported / unsupported region lookup
│   └── test_Bedrock__Setup__Renderer.py       ← IAM JSON shape, deeplink URL
└── cli/
    └── test_Cli__Bedrock__check_and_setup.py  ← CliRunner-driven verb smoke
```

No `monkeypatch` — follow the Slice A / E / H pattern (subclass the AWS client, override the boto3 seam).

---

## Generalisation (for the umbrella)

The `check` / `setup` pattern is broader than Bedrock. Same shape would help:

- **`sg aws s3 check`** — does the role have `s3:ListBuckets`? Does the default bucket exist? Is the role's region the same as the bucket's region?
- **`sg aws fargate check`** — does the role have `ecs:RunTask`? Does the target cluster exist? Are the task-definition's images pullable from the registry?
- **`sg aws iam graph check`** — does the role have IAM read perms? Can it list more than N roles (catalogue size)?
- **`sg aws creds check`** — does the role have `sts:AssumeRole` for the scope's target role?

I'd propose adding **§4 to the umbrella's `01__scope-and-architecture.md`** to make `check` a first-class convention for every `sg aws X` namespace:

> ### 4.1 The `check` convention
>
> Every `sg aws X` namespace ships a `check` verb. It runs a series of cheap diagnostic probes (IAM permissions, region support, resource existence, smoke-test a representative call) and prints a Rich-panel diagnostic table. Exits 1 on any FAIL, 0 with stderr warning on any WARN, 0 silently on all PASS. **Never mutates.** The output format is shared via `aws/_shared/Check__Renderer.py` so users see the same table shape across surfaces.

Bedrock is the first surface to implement this. A v0.2.30 sweep brings the others up.

The `setup` verb is a per-surface concern (each surface has its own IAM permissions and AWS-console deeplinks) but the renderer for IAM JSON + deeplinks could live in `aws/_shared/Setup__Renderer.py`.

---

## Open questions

| # | Question | Default if undecided |
|---|----------|----------------------|
| 1 | Should `check` be gated on the active sg role (require one) or work with whatever boto3 picks up? | Work with either — fail check #1 (caller-identity) if no creds, otherwise proceed |
| 2 | Should `setup --apply` ship in v0.2.29 or defer to v0.2.30 with Slice G? | Defer — print-and-open in v0.2.29 |
| 3 | Should the curated `Bedrock__Region__Catalogue` be a hardcoded constant or queried from the AWS regions API? | Hardcoded for v0.2.29 (Bedrock GA region list rarely changes); query from `bedrock` SSM parameter `/aws/service/global-infrastructure/services/bedrock/regions/...` in v0.2.30 |
| 4 | If invoke-perm smoke-test costs money, is that OK in a default `check` run? | Yes — Claude Haiku at 1 token costs $0.0000004; bound via existing `Bedrock__Cost__Calculator.check_cost_cap` |
| 5 | If the user hasn't enabled any model, can check still emit useful info? | Yes — drop the invoke-perm smoke-test, return ⚠ on check 7 with "skipped — no models enabled" |
| 6 | Should `check --json` exist? | Yes — return `List__Schema__Bedrock__Check__Result.json()` for scripting / `sg aws observe` ingestion |

---

## Acceptance commands

```bash
# Happy path
sg aws bedrock check                              # all ✓ → exit 0, prints table
sg aws bedrock check --json | jq '.[] | select(.status=="FAIL")'

# No model access
sg aws bedrock check                              # ⚠ on check 5, ✗ on check 6, exit 1
sg aws bedrock setup --open-console               # browser opens
sg aws bedrock setup --print-policy > policy.json
aws iam put-role-policy --role-name dev --policy-name SgAwsBedrockChat \
    --policy-document file://policy.json
# (user enables Claude Haiku in the console)
sg aws bedrock check                              # all ✓
sg aws bedrock chat claude --prompt "say ok"      # works

# No IAM perm to list-models
sg aws bedrock chat list-models                   # NEW: clear error, not "0 models"
#   → [✗] Permission denied: bedrock:ListFoundationModels
#     Run:  sg aws bedrock setup --print-policy

# Wrong region (Bedrock not GA there)
sg aws bedrock check --region ca-west-1           # check 2 fails with named region list
```

---

## Scope (what this brief is + isn't)

**Is:** UX improvement to Slice E. Three verbs / fixes (`check`, `setup`, `list-models` error path). Forward-compatible flag for the v0.2.30 `--apply` story.

**Isn't:**
- Not implementing model-access via API (AWS console is the only path)
- Not implementing IAM policy attachment (waits for Slice G)
- Not rolling out `check` to other surfaces (umbrella §4 convention; per-surface work)

---

## Pointer back

- Parent pack: [`README.md`](README.md) — Slice E brief
- Architect review that flagged the silent-exception pattern (M-1): [`team/roles/architect/reviews/05/17/v0.2.29__slice-b-ec2__review.md`](../../../team/roles/architect/reviews/05/17/v0.2.29__slice-b-ec2__review.md)
- Existing diagnostic pattern: `sg doctor preflight` at `scripts/doctor.py`
- Sg__Aws__Session credentials seam (for check #1 + setup #1): `sgraph_ai_service_playwright__cli/credentials/service/Sg__Aws__Session.py`
