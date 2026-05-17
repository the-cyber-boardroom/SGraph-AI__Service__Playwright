# Reality — SP CLI Lambda Deployment (standalone)

**Status:** buildable — everything to deploy the SP CLI as its own Lambda
exists in code. First live deploy has not yet run (no cloud-side evidence
in this repo yet).

The SP CLI FastAPI app (slice 3) is deployed as its **own** AWS Lambda, with
its **own IAM role**, its **own ECR repository**, and its **own Function
URL**. No changes to `Fast_API__Playwright__Service` or its Lambda.

---

## Why standalone (not mounted into the main service)

- **Security boundary** — the main Playwright service does not need
  `ec2:RunInstances` or `iam:PassRole`. Keeping those powers on a separate
  role shrinks the blast radius if the Playwright Lambda is compromised.
- **Scaling / billing / monitoring** independent from the browser service.
- **Matches the brief** — v0.1.72 frames this API as the one GH Actions
  hits on a schedule; a separate Function URL is cleaner for that.

---

## IAM role: `sp-playwright-cli-lambda`

Trust policy: only `lambda.amazonaws.com` can assume. **All five sp-cli-*
policies are INLINE** (attached via `put_role_policy`) — not customer-managed
standalone resources. Rationale:

- Smaller CI permissions footprint: the deploy identity needs only
  `iam:PutRolePolicy` (per-role), not `iam:CreatePolicy` +
  `iam:AttachRolePolicy` (account-level).
- Zero orphan cleanup — deleting the role removes the policies too.
- `put_role_policy` is naturally idempotent.

| Inline policy | Scope |
|---------------|-------|
| `AWSLambdaBasicExecutionRole` (managed, attached by ARN) | CloudWatch logs |
| `sp-cli-ec2-management`                 | `ec2:RunInstances / TerminateInstances / Describe* / CreateSecurityGroup / AuthorizeSecurityGroup* / CreateTags` — all on `Resource: *` (EC2 does not support resource-level scoping on RunInstances without elaborate tag conditions) |
| `sp-cli-iam-passrole`                   | `iam:PassRole` ARN-scoped to `arn:aws:iam::{account}:role/playwright-ec2`, condition `iam:PassedToService = ec2.amazonaws.com`. Plus `iam:Get/CreateInstanceProfile / AddRoleToInstanceProfile` on the same role + profile. Never `*`. |
| `sp-cli-ecr-read`                       | Pull-only: `GetAuthorizationToken / BatchGetImage / DescribeImages`. No push rights. |
| `sp-cli-sts-helpers`                    | `sts:GetCallerIdentity`, `sts:DecodeAuthorizationMessage` — for preflight + the auto-decode error pretty-printer. |
| `sp-cli-observability`                  | READ + DELETE only. `aps:List/Describe/DeleteWorkspace` (AMP), `es:List/Describe/DeleteDomain` + `es:ESHttpGet` (OpenSearch, incl. the SigV4 doc-count call), `grafana:List/Describe/DeleteWorkspace`. No create or update actions. |

---

## Image: `sp-playwright-cli`

- **Base:** `public.ecr.aws/lambda/python:3.12` — no Chromium (not needed here).
- **Handler:** `sgraph_ai_service_playwright__cli.fast_api.lambda_handler.handler` (Mangum wraps the FastAPI app).
- **Build context:** repo root. `.dockerignore` keeps only `sgraph_ai_service_playwright__cli/` + `scripts/`.

## Lambda: `sp-playwright-cli-{stage}`

| Setting | Value | Rationale |
|---------|-------|-----------|
| Memory  | 1024 MB | Adapter Lambda — all heavy work is AWS API calls |
| Timeout | 120 s   | `sp create` is ~60 s, 2× buffer |
| Architecture | x86_64 | Base image tag |
| Function URL | AuthType=NONE | API-key middleware inside the app gates every route |

Env vars (propagated from the CI process):
- `FAST_API__AUTH__API_KEY__NAME`  (default `X-API-Key`)
- `FAST_API__AUTH__API_KEY__VALUE` (required — middleware rejects all without)
- `AWS_DEFAULT_REGION`

---

## Files added

### `sgraph_ai_service_playwright__cli/deploy/`

| File | Role |
|------|------|
| `images/sp_cli/dockerfile`          | Image definition |
| `images/sp_cli/requirements.txt`    | Lambda runtime deps (no Playwright) |
| `images/sp_cli/.dockerignore`       | Scopes the build context |
| `SP__CLI__Lambda__Policy.py`        | Type_Safe — returns IAM policy dicts |
| `SP__CLI__Lambda__Role.py`          | Creates / updates the IAM role via `osbot-aws.IAM_Role` |
| `Docker__SP__CLI.py`                | Image paths + ECR build/push |
| `Lambda__SP__CLI.py`                | Lambda upsert + Function URL (two-statement AuthType=NONE pattern) |
| `provision.py`                      | Orchestrator: role → image → Lambda; `python -m ... --stage dev` |

### Tests (18 new; 52 total)

| File | Coverage |
|------|----------|
| `tests/unit/.../deploy/test_SP__CLI__Lambda__Policy.py` | 8 cases — shape of each policy, security-critical assertions (PassRole not `*`; ECR pull-only; trust policy Lambda-only) |
| `tests/unit/.../deploy/test_Docker__SP__CLI.py`         | 6 cases — dockerfile + requirements + .dockerignore exist; handler path + base image match |
| `tests/unit/.../deploy/test_Lambda__SP__CLI.py`         | 4 cases — lambda name, handler path, tuning constants |

---

## How to deploy

```bash
# One-time: ensure FAST_API__AUTH__API_KEY__VALUE + AWS_DEFAULT_REGION
# are set in the environment. AWS credentials must carry iam:CreateRole,
# iam:AttachRolePolicy, ecr:CreateRepository, lambda:CreateFunction /
# lambda:UpdateFunctionConfiguration (plus the build-push ECR permissions).

python -m sgraph_ai_service_playwright__cli.deploy.provision --stage dev
```

Idempotent — re-run on every change to roll the image + refresh env vars.
Prints the Function URL on success.

---

## CI workflow

`.github/workflows/ci__sp_cli.yml` — runs on push/PR to any of
`sgraph_ai_service_playwright__cli/**`, `scripts/provision_ec2.py`,
`scripts/observability.py`, the workflow itself, or the SP CLI unit tests.
Also triggerable via `workflow_dispatch` with optional stage override +
`force_image_rebuild` toggle.

| Job | What it does |
|-----|--------------|
| `run-unit-tests`          | `pytest tests/unit/sgraph_ai_service_playwright__cli/` |
| `check-aws-credentials`   | Gate — skips AWS-touching jobs when `AWS_ACCESS_KEY_ID` etc. are missing |
| `detect-changes`          | paths-filter — skips image rebuild on test-only churn |
| `build-and-push-image`    | `Docker__SP__CLI().setup().build_and_push()` — repo-root context |
| `provision-sp-cli-lambda` | `python -m sgraph_ai_service_playwright__cli.deploy.provision --stage <resolved>` — runs even when the image is reused so role/env-var tweaks land idempotently |

Stage resolution: `workflow_dispatch` input wins; else `main` → `prod`, any
other branch → `dev`.

## Known gaps / follow-ups

1. **No live verification** — all tests are unit-level. Follow-up
   deploy-via-pytest (numbered tests: `test_1__ensure_role`, `test_2__build_push_image`, etc.) would provide real-AWS confidence, mirroring `tests/deploy/`.
2. **Type_Safe 422 issue** — the framework still returns HTTP 500 on
   invalid request bodies (carried over from slice 3; not specific to the
   Lambda).
