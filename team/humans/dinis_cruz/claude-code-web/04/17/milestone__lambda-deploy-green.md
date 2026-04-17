# Milestone — Lambda deploy is green end-to-end

**Date:** 2026-04-17
**Session branch:** `claude/general-session-HRsiq`

---

## TL;DR

From a **deleted Lambda**, the CI pipeline now:

1. Builds the Docker image (Playwright 1.58.0-noble + LWA 1.0.0) — `build-docker-image` job
2. Pushes it to ECR — `push-to-ecr` job
3. Runs in-container integration tests against real Chromium — `run-integration-tests` job
4. Creates a fresh Lambda (`memory_size=5120`, `architecture=x86_64`, `timeout=300s`) — `deploy-lambda` job, step `test_1__create_lambda`
5. Creates a public Function URL with **both** required IAM statements — same step
6. Invokes `/health/status` over real HTTP with the API-key header — `test_3__invoke__function_url`
7. Runs the smoke suite against the deployed URL — `smoke-test` job

No manual console clicks needed.

---

## What we fixed this session

### 1. `Runtime.ExitError` at 110 ms — the `memory_size` trap

**Symptom:** Lambda boots, Playwright cold-starts, container dies at ~110 ms with `Runtime.ExitError`. AWS console shows the function at **512 MB**, not the 5120 MB we thought we set.

**Root cause:** `osbot_aws.aws.lambda_.Lambda` reads `self.memory_size` when it builds the boto3 `create_function` kwargs. Our code set `lambda_function.memory = 5120`, which silently created a useless attribute. The class then fell through to the default 512 MB, which is far below what Playwright needs for Chromium cold start.

**Fix:** one-line change — `lambda_function.memory_size = LAMBDA_MEMORY_MB` (file: `sgraph_ai_service_playwright/docker/Lambda__Docker__SGraph_AI__Service__Playwright.py`).

**Burnt in as a comment** at the top of the file so nobody else falls into this:
```python
#   memory_size   = 5120 MB  (osbot_aws reads `memory_size`, NOT `memory` — the
#                             wrong attr silently falls back to 512 MB and
#                             Playwright OOMs at cold start with Runtime.ExitError)
```

### 2. `403 Forbidden` on the Function URL — the two-statement trap

**Symptom:** Lambda is `Active`, Function URL is created, `curl` returns 403. Manually deleting + recreating the URL in the AWS console fixed it. The console creates **two** resource-based policy statements; osbot_aws only created one.

**Root cause:** per [AWS docs (October 2025)](https://docs.aws.amazon.com/lambda/latest/dg/urls-auth.html), public Function URLs (`AuthType=NONE`) need two resource-based policy statements:

| # | StatementId | Action | Condition |
|---|---|---|---|
| 1 | `FunctionURLAllowPublicAccess` | `lambda:InvokeFunctionUrl` | `StringEquals {"lambda:FunctionUrlAuthType": "NONE"}` |
| 2 | `FunctionURLInvokeAllowPublicAccess` | `lambda:InvokeFunction` | `Bool {"lambda:InvokedViaFunctionUrl": "true"}` |

`osbot_aws.function_url_create_with_public_access()` emits **only the first**. `osbot_aws.permission_add()` has no parameter for `InvokedViaFunctionUrl`, and passing `FunctionUrlAuthType='NONE'` on an `InvokeFunction` action produces the wrong condition.

**Fix:** keep osbot_aws for the URL + statement 1, drop to boto3 directly for statement 2:

```python
boto3_client.add_permission(FunctionName           = function_name,
                            StatementId            = 'FunctionURLInvokeAllowPublicAccess',
                            Action                 = 'lambda:InvokeFunction',
                            Principal              = '*',
                            InvokedViaFunctionUrl  = True)
```

This is a documented, narrow exception to CLAUDE.md rule #11 ("Never use boto3 directly"). The header comment explains why.

### 3. Test assertions that used to pass silently

`test_1__create_lambda` used to assert only `create_result.status != 'error'`. We hardened it so the two-statement proof is part of the test:

```python
assert result.get('create_result', {}).get('status')            == 'ok'
assert result.get('function_url' , {}).get('auth_type')         == 'NONE'
assert result.get('function_url' , {}).get('url_policy')        is not None   # statement 1
assert result.get('function_url' , {}).get('invoke_permission') is not None   # statement 2
```

### 4. `test_2__invoke__health_info` — proper APIGW v2 event shape

The earlier `{path, httpMethod, headers}` payload didn't work because Lambda Web Adapter expects an **API Gateway v2** event when the Lambda is invoked directly (i.e., not via the Function URL). We now build a minimal-but-complete APIGW v2 event (`version: '2.0'`, `rawPath`, `requestContext.http.method`, etc.).

### 5. `Routes__Set_Cookie` wired into the FastAPI app

Added:
```python
from osbot_fast_api.api.routes.Routes__Set_Cookie import Routes__Set_Cookie
self.add_routes(Routes__Set_Cookie)
```

This exposes `/auth/set-cookie-form` (HTML UI) and `/auth/set-auth-cookie` (POST), both in `AUTH__EXCLUDED_PATHS` so they bypass the API-key middleware. Nice-to-have for setting up the auth cookie from a browser.

---

## Files touched

| File | What changed |
|---|---|
| `sgraph_ai_service_playwright/docker/Lambda__Docker__SGraph_AI__Service__Playwright.py` | `memory_size` fix; boto3 direct for statement 2; `timeout=300s`; `set_lambda_env_vars` now also propagates `FAST_API__AUTH__API_KEY__*`; header comment explaining both traps |
| `sgraph_ai_service_playwright/fast_api/Fast_API__Playwright__Service.py` | `Routes__Set_Cookie` registered |
| `tests/deploy/test_Deploy__Playwright__Service__base.py` | Strengthened `test_1` assertions; APIGW v2 event in `test_2`; gated on `FAST_API__AUTH__API_KEY__*` |
| `.github/workflows/ci-pipeline.yml` | Re-enabled all jobs (removed the `if: false` shortcuts we used during the debug cycle); restored `deploy-lambda`'s full `needs: [push-to-ecr, run-integration-tests, check-aws-credentials]` gate |
| `team/explorer/librarian/reality/v0.1.0__what-exists-today.md` | Updated to reflect the now-working Lambda deploy path |

---

## What's still known-broken / next phase

- **Phase 2.10** is next: `Action__Runner` + `Sequence__Runner` + the remaining three route classes (`Routes__Session`, `Routes__Browser`, `Routes__Sequence`). This fills in the session/action/sequence surface on `Playwright__Service`.
- **Phase 2.11** after that: the 10 deferred `Step__Executor` action handlers (`PRESS`, `SELECT`, `HOVER`, `SCROLL`, `WAIT_FOR`, `VIDEO_START`, `VIDEO_STOP`, `EVALUATE`, `DISPATCH_EVENT`, `SET_VIEWPORT`).
- Real vault HTTP client + osbot-aws S3 adapter for `Artefact__Writer` (today they are subclass-overridable seams).
- `__to__main` / `__to__prod` deploy-test subclasses (only `__to__dev` is wired today).

The Lambda deploy is no longer on the critical path — it just works. Focus can move back to features.
