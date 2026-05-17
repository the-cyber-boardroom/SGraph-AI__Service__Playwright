---
title: "05 — Agent B — Lambda experiments + sg aws lambda expansion (P2)"
file: 05__agent-B__lambda-experiments.md
author: Architect (Claude)
date: 2026-05-17
parent: README.md
size: L (large) — ~2200 prod lines, ~700 test lines, ~2.5 days
depends_on: Foundation PR
delivers: lab P2 from lab-brief/07 + the sg aws lambda primitive expansion (Decision #9)
---

# Agent B — Lambda experiments + `sg aws lambda` expansion

The biggest single slice. Builds both the lab Lambda experiments **and** the `sg aws lambda` primitive verbs the v2 brief needs.

---

## Part 1 — Lab Lambda experiments

**Folder:** `sgraph_ai_service_playwright__cli/aws/lab/service/experiments/lambda_/`

**Files to create:**

| File | Tier | Experiment |
|------|------|------------|
| `E30__lambda_cold_start.py` | 1 | Q4 — cold-start time distribution |
| `E31__lambda_deps_impact.py` | 1 | Q4 — osbot-utils / osbot-aws cost at cold start |
| `E32__lambda_stream_vs_buffer.py` | 1 | Streaming vs buffered, concrete numbers |
| `E33__lambda_internal_r53_call.py` | 1 | Q5 — `upsert_record` latency from inside the Lambda |
| `E34__lambda_internal_ec2_curl.py` | 1 | Q5 — Lambda → EC2 network cost |
| `E35__lambda_function_url_vs_direct.py` | 1 | Function URL HTTPS vs `lambda.invoke` direct |

**Plus:**
- `service/teardown/Lab__Teardown__Lambda.py` — full implementation (delete URL → delete function)
- `service/teardown/Lab__Teardown__IAM.py` — full implementation (detach policies → delete role; lab-tagged roles only)
- `service/lambdas/lab_waker_stub/` — FastAPI + Lambda Web Adapter, returns warming HTML or echo
- `service/lambdas/lab_error_origin/` — returns 503/502/timeouts per query param (Agent C also uses this)
- `service/lambdas/lab_internal_caller/` — times internal AWS calls (E33, E34)
- `service/temp_clients/Lab__Lambda__Client__Temp.py` — boto3 wrapper, tagged for deletion in P-Swap
- `schemas/Schema__Lab__Result__Lambda__*.py` — one file per result shape
- `service/renderers/Render__Histogram__ASCII.py` — fill in `render_durations_ms(...)`
- Registration lines in `service/experiments/registry.py` (6 entries)

---

## Part 2 — `sg aws lambda` primitive expansion

**Decision #9** folds these into this slice. Five new verbs that the v2 brief needs and the lab uses internally:

| Verb | Purpose | Used by |
|------|---------|---------|
| `<name> deploy-from-image` | Deploy from an ECR container image | v2 brief (waker as container) |
| `<name> alias {create,list,update,delete}` | Lambda alias management | E33 (calls internal R53); v2 versioning |
| `<name> permissions {add,list,remove}` | Resource-policy management (e.g. allow CF to invoke) | E25/E26 (CF→Lambda); v2 brief |
| `<name> concurrency {get,set,clear}` | Reserved-concurrency control | Lab safety guard (cap lab Lambdas to 2) |
| `<name> env {get,set,unset}` | Env-var management | Convenience verb |

**Files to create / extend:**

- `aws/lambda_/cli/verb_alias.py` (or follow existing per-verb file convention — inspect `verb_logs.py` for shape)
- `aws/lambda_/cli/verb_permissions.py`
- `aws/lambda_/cli/verb_concurrency.py`
- `aws/lambda_/cli/verb_env.py`
- `aws/lambda_/cli/verb_deploy_from_image.py`
- `aws/lambda_/service/Lambda__AWS__Client.py` — add `add_permission`, `remove_permission`, `get_policy`, `create_alias`, `update_alias`, `delete_alias`, `list_aliases`, `put_function_concurrency`, `get_function_concurrency`, `delete_function_concurrency`, `update_function_configuration` (env subset), `create_function_from_image`
- `aws/lambda_/service/Lambda__Deployer.py` — extend with `deploy_from_image(image_uri, ...)` path

Plus matching tests under `tests/unit/sgraph_ai_service_playwright__cli/aws/lambda_/`.

**Update the user docs** in `library/docs/cli/sg-aws/07__lambda.md` — move the "Not yet implemented" entries for `tags / versions / aliases` into the live section, add the new verbs.

---

## What you do NOT touch

- `experiments/dns/`, `experiments/cf/`, `experiments/transition/`
- `Lab__Teardown__{R53,CF,ACM,EC2,SSM}.py`
- `aws/dns/` and `aws/cf/` packages
- `serve`, `runs diff`, HTML viewer — Agent E

---

## Reuse, don't rewrite

| Existing class | Path | Use for |
|---------------|------|---------|
| `Lambda__AWS__Client` | `aws/lambda_/service/` | Existing list/get/CRUD/invoke. Extend; don't replace. |
| `Lambda__Deployer` | `aws/lambda_/service/` | Existing zip+deploy. Extend with image-based path. |
| `Lambda__Name__Resolver` | `aws/lambda_/service/` | Fuzzy name resolution (existing) |
| `osbot_aws.aws.lambda_.Deploy_Lambda` | osbot-aws | The deploy primitive |
| `Logs__AWS__Client` | `aws/logs/service/` | For experiments that read function logs post-invoke |

---

## Risks to watch

- **In-tree Lambdas accidentally deploy real business logic.** The three `lab_*` Lambdas are deliberately tiny — handler + requirements.txt only. Reject any PR review where these grow beyond ~50 lines each.
- **Cold-start measurements need real eviction.** E30's container-eviction strategy is "update the Lambda configuration to force a new container" (per `lab-brief/03 §E30 step 3`). A 10-min `--cold-spacing` is the fallback. Don't rely on idle eviction alone — AWS no longer evicts on a tight schedule.
- **Reserved concurrency must be set.** Every lab Lambda gets `reserved_concurrency=2` to cap blast radius if a lab Lambda recurses. Apply this in `Lab__Teardown__Lambda.py`'s create-counterpart helper (or in the `lab_waker_stub` deploy).
- **Function URLs must be NONE auth for lab use.** That's the whole point — measure the public path. Document loudly in CLI help that `--auth-type NONE` is the lab default but should never be the default for real Lambdas.
- **Streaming-mode requires a separate Lambda config.** E32 needs two Lambdas (BUFFERED + RESPONSE_STREAM) — don't try to toggle on one.

---

## Acceptance

```bash
sg aws lab list                                       # 6 Lambda experiments now visible (15 total with DNS)

SG_AWS__LAB__ALLOW_MUTATIONS=1 sg aws lab run E30 --repeat 5        # cold-start hist
SG_AWS__LAB__ALLOW_MUTATIONS=1 sg aws lab run E32 --body-size 1MB,5MB

# new sg aws lambda verbs
SG_AWS__LAMBDA__ALLOW_MUTATIONS=1 sg aws lambda waker alias create staging --version 3
sg aws lambda waker alias list
SG_AWS__LAMBDA__ALLOW_MUTATIONS=1 sg aws lambda waker permissions add \
  --statement-id allow-cf --principal cloudfront.amazonaws.com \
  --action lambda:InvokeFunctionUrl
sg aws lambda waker permissions list
sg aws lambda waker env get
SG_AWS__LAMBDA__ALLOW_MUTATIONS=1 sg aws lambda waker concurrency set 2

sg aws lab sweep                                      # → "no leaked resources"
```

Plus the unit + Lambda safety integration tests:

```bash
pytest tests/unit/sgraph_ai_service_playwright__cli/aws/lab/experiments/lambda_/ -v
pytest tests/unit/sgraph_ai_service_playwright__cli/aws/lambda_/ -v
SG_AWS__LAB__ALLOW_MUTATIONS=1 SG_AWS__LAB__DESTROY_TEST=1 \
  pytest tests/integration/sgraph_ai_service_playwright__cli/aws/lab/test_safety_lambda.py
```

---

## Commit + PR

Branch: `claude/aws-primitives-support-NVyEh-lambda`. Commit prefix: `feat(v0.2.28): lab agent-B — Lambda experiments + sg aws lambda expansion`.

Open PR against `claude/aws-primitives-support-NVyEh`.
