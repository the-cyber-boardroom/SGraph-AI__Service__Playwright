---
title: "05 — Agent B — Lambda experiments (P2)"
file: 05__agent-B__lambda-experiments.md
author: Architect (Claude)
date: 2026-05-17 (rev 2)
parent: README.md
size: M (medium) — ~1200 prod lines, ~500 test lines, ~1.5 days
depends_on: Foundation PR + v2 vault-publish phase 2b (sg aws lambda expansion)
mandatory_reading:
  - team/humans/dinis_cruz/claude-code-web/05/17/00/v0.2.23__plan__vault-publish-spec/03__delta-from-lab-brief.md  # §B.1 — §B.7
delivers: lab P2 from lab-brief/07
---

# Agent B — Lambda experiments

Lab Lambda experiments composed on top of the **v2 vault-publish-shipped `sg aws lambda` expansion**.

---

## Sequencing — DO NOT START EARLY

This slice **cannot ship before v2 vault-publish phase 2b lands**. Phase 2b is where the `sg aws lambda <name> {alias, permissions, deploy-from-image, concurrency, env}` verbs (and the matching `Lambda__AWS__Client` extensions) are added. Rev 2 of this pack explicitly dropped the temp-boto3-wrapper fallback (decision #2) so there's no "use Temp client until then" path.

The Opus coordinator fires Agent B **only after v2 phase 2b merges to `dev`** and the integration branch has been rebased onto it.

---

## What you own

**Folder:** `sgraph_ai_service_playwright__cli/aws/lab/service/experiments/lambda_/`

**Files to create** (per delta `B.3` — file names match class names, no `E30__` prefix):

| File | Tier | Experiment |
|------|------|------------|
| `Lab__Experiment__Lambda__Cold_Start.py` | 1 | Q4 — cold-start time distribution |
| `Lab__Experiment__Lambda__Deps_Impact.py` | 1 | Q4 — osbot-utils / osbot-aws cost at cold start |
| `Lab__Experiment__Lambda__Stream_Vs_Buffer.py` | 1 | Streaming vs buffered, concrete numbers |
| `Lab__Experiment__Lambda__Internal_R53_Call.py` | 1 | Q5 — `upsert_record` latency from inside the Lambda |
| `Lab__Experiment__Lambda__Internal_EC2_Curl.py` | 1 | Q5 — Lambda → EC2 network cost |
| `Lab__Experiment__Lambda__Function_URL_Vs_Direct.py` | 1 | Function URL HTTPS vs `lambda.invoke` direct |

**Plus:**
- `service/teardown/Lab__Teardown__Lambda.py` — full implementation. **Uses `Lambda__AWS__Client` directly** (which routes through `Sg__Aws__Session.from_context().boto3_client_from_context()` per decision #6).
- `service/teardown/Lab__Teardown__IAM.py` — full implementation (detach policies → delete role; lab-tagged roles only). Uses existing `IAM__AWS__Client`.
- `service/lambdas/lab_waker_stub/` — FastAPI + Lambda Web Adapter, returns warming HTML or echo
- `service/lambdas/lab_error_origin/` — returns 503/502/timeouts per query param (Agent C also uses this)
- `service/lambdas/lab_internal_caller/` — times internal AWS calls (E33, E34)
- `schemas/Schema__Lab__Result__Lambda__*.py` — one file per result shape. **Per delta `B.1` and `B.4`**: no `Set__Str` / `Dict__Str__Str` field types — use `Type_Safe__Dict__Safe_Str__Safe_Str` (etc.).
- `service/renderers/Render__Histogram__ASCII.py` — fill in `render_durations_ms(...)` (foundation ships the stub)
- Registration lines in `service/experiments/registry.py` (6 entries)

**Experiment-class shape — per delta `B.2`:**

```python
class Lab__Experiment__Lambda__Cold_Start(Lab__Experiment):
    name           : Safe_Str__Lab__Experiment_Name = 'lambda-cold-start'
    tier           : Enum__Lab__Tier                = Enum__Lab__Tier.MUTATING_LOW
    runner         : Lab__Runner                                          # injected at setup, NOT a parameter to execute()
    repeat         : Safe_Int__Repeat__Count        = 20

    def setup(self, runner: Lab__Runner, repeat: int = 20) -> 'Self':
        self.runner = runner
        self.repeat = repeat
        return self

    def execute(self) -> Schema__Lab__Run__Result:
        ...
```

---

## What you do NOT touch

- `experiments/dns/`, `experiments/cf/`, `experiments/transition/`
- `Lab__Teardown__{R53,CF,ACM,EC2,SSM}.py`
- **`aws/lambda_/` package** — NO primitive expansion in this PR. The expansion (verbs `alias`, `permissions`, `deploy-from-image`, `concurrency`, `env`) is owned by v2 vault-publish phase 2b. If you find you need a verb that doesn't exist there yet, **stop and escalate** — do not add it.
- `aws/dns/` and `aws/cf/` packages
- `serve`, `runs diff`, HTML viewer — Agent E

---

## Reuse, don't rewrite

| Existing class | Path | Use for |
|---------------|------|---------|
| `Lambda__AWS__Client` | `aws/lambda_/service/` | **Today's baseline**: list / get / CRUD / invoke / Function-URL ops. Some primitives like `add_permission` are called via bare boto3 inside other methods but are not yet public wrappers. **By the time you start**, v2 phase 2b will have exposed `create_alias` / `add_permission` / `create_function_from_image` / `put_function_concurrency` / `update_function_configuration` (env subset) as public methods. |
| `Lambda__Deployer` | `aws/lambda_/service/` | Existing zip + v2's image-based path |
| `Lambda__Name__Resolver` | `aws/lambda_/service/` | Fuzzy name resolution (existing) |
| `IAM__AWS__Client` | `aws/iam/service/` | Existing — creates the per-lab-Lambda execution role |
| `Logs__AWS__Client` | `aws/logs/service/` | Reads function logs post-invoke (for cold-start measurement) |
| `Sg__Aws__Session` | `credentials/service/` | The AWS-client seam — `from_context().boto3_client_from_context(...)` for everything |
| `osbot_aws.aws.lambda_.Deploy_Lambda` | osbot-aws | Underlying deploy primitive |

---

## Risks to watch

- **In-tree Lambdas accidentally deploy real business logic.** The three `lab_*` Lambdas are deliberately tiny — handler + requirements.txt only. Reject any PR review where these grow beyond ~50 lines each.
- **Cold-start measurements need real eviction.** E30's container-eviction strategy is "update the Lambda configuration to force a new container" (per `lab-brief/03 §E30 step 3`). A 10-min `--cold-spacing` is the fallback. Don't rely on idle eviction alone — AWS no longer evicts on a tight schedule.
- **Reserved concurrency must be set.** Every lab Lambda gets `reserved_concurrency=2` to cap blast radius if a lab Lambda recurses. Apply this via the v2-shipped `sg aws lambda <name> concurrency set` verb in `Lab__Teardown__Lambda`'s create-counterpart helper.
- **Function URLs must be NONE auth for lab use.** That's the whole point — measure the public path. Per decision Q6 (RESOLVED via v0.2.23 plan Q8) `auth_type='NONE'` is the lab default. The lab Lambda is torn down in <1 hour so the risk is bounded.
- **Streaming-mode requires a separate Lambda config.** E32 needs two Lambdas (BUFFERED + RESPONSE_STREAM) — don't try to toggle on one.

---

## Acceptance

```bash
sg aws lab list                                                                # 6 Lambda experiments now visible (15 total with DNS)

SG_AWS__LAB__ALLOW_MUTATIONS=1 sg aws lab run lambda-cold-start --repeat 5
SG_AWS__LAB__ALLOW_MUTATIONS=1 sg aws lab run lambda-stream-vs-buffer --body-size 1MB,5MB

sg aws lab sweep                                                               # → "no leaked resources"

# unit tests
pytest tests/unit/sgraph_ai_service_playwright__cli/aws/lab/experiments/lambda_/ -v

# safety integration test (gated)
SG_AWS__LAB__ALLOW_MUTATIONS=1 SG_AWS__LAB__DESTROY_TEST=1 \
  pytest tests/integration/sgraph_ai_service_playwright__cli/aws/lab/test_safety_lambda.py
```

---

## Commit + PR

Branch: `claude/aws-primitives-support-NVyEh-lambda`. Commit prefix: `feat(v0.3.0): lab agent-B — Lambda experiments`.

Open PR against `claude/aws-primitives-support-NVyEh`.
