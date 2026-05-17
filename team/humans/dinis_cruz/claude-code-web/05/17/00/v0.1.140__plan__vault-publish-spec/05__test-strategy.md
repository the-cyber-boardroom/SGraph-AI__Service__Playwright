---
title: "05 — Test strategy"
file: 05__test-strategy.md
author: Architect (Claude — code-web session)
date: 2026-05-17 (UTC hour 00)
parent: README.md
---

# 05 — Test strategy

The plan obeys the four non-negotiables from `library/guides/v3.1.1__testing_guidance.md`:

1. **No mocks. No patches.** Composition via `*__In_Memory` subclasses.
2. **Assert on contracts** (schemas, status codes, persisted state) — not implementation details.
3. **Real Chromium for integration tests** — gate on `SG_PLAYWRIGHT__CHROMIUM_EXECUTABLE`; skip cleanly when absent. **(Vault-publish has no Playwright surface — this rule applies only to integration tests that depend on the substrate's `--with-playwright` mode, which is off for vault-publish; no test in this plan needs Chromium.)**
4. **Deploy-via-pytest.** Tests are numbered (`test_1__create_lambda`, `test_2__invoke__health_info`, …) and run top-down.

---

## 1. Test layout

Mirror the codebase convention. Verified — `tests/unit/sgraph_ai_service_playwright__cli/aws/dns/` exists; `sg_compute_specs/vault_app/tests/` exists (in-package tests for the spec).

### 1.1 Spec-internal tests (live with the spec)

```
sg_compute_specs/vault_publish/tests/
├── __init__.py
├── test_Safe_Str__Slug.py
├── test_Slug__Validator.py
├── test_Slug__Registry.py                       # in-memory Parameter
├── test_Reserved__Slugs.py
├── test_Vault_Publish__Service.py               # in-memory vault_app + registry + r53
├── test_Vault_Publish__Service__bootstrap.py    # phase 2d
├── test_Cli__Vault_Publish.py                   # golden-file CLI
└── waker/
    ├── __init__.py
    ├── test_Slug__From_Host.py
    ├── test_Endpoint__Resolver__EC2.py
    ├── test_Endpoint__Proxy.py
    ├── test_Warming__Page.py
    └── test_Waker__Handler.py
```

### 1.2 Platform-primitive tests (under `tests/unit/`)

```
tests/unit/sgraph_ai_service_playwright__cli/aws/cf/
├── service/
│   ├── CloudFront__AWS__Client__In_Memory.py
│   ├── test_CloudFront__AWS__Client.py
│   ├── test_CloudFront__Distribution__Builder.py
│   └── test_CloudFront__Origin__Failover__Builder.py
├── cli/
│   └── test_Cli__Cf.py
└── schemas/
    └── test_Schema__CF.py                       # consolidated; per-class field defaults + type guards

tests/unit/sgraph_ai_service_playwright__cli/aws/lambda_/
├── service/
│   ├── Lambda__AWS__Client__In_Memory.py
│   ├── test_Lambda__AWS__Client.py
│   ├── test_Lambda__Deployer.py
│   └── test_Lambda__Url__Manager.py
├── cli/
│   └── test_Cli__Lambda.py
└── schemas/
    └── test_Schema__Lambda.py
```

---

## 2. In-memory fixtures — reuse vs build

### 2.1 Already exist (REUSE)

| Fixture | Path | Reused by |
|---------|------|-----------|
| `Ec2__Service__In_Memory` | `tests/unit/sgraph_ai_service_playwright__cli/ec2/service/Ec2__Service__In_Memory.py` | (potential) Waker integration tests if EC2_Instance needs a backing surface |
| `Caller__IP__Detector__In_Memory` | `tests/unit/sgraph_ai_service_playwright__cli/elastic/service/Caller__IP__Detector__In_Memory.py` | `Vault_App__Service.create_stack` paths during phase 1a regression tests |
| `Elastic__AWS__Client__In_Memory` etc. | `tests/unit/sgraph_ai_service_playwright__cli/elastic/service/` | Reference pattern, not directly reused |
| `Vault_App__AWS__Client__In_Memory` | (likely exists — verify under `sg_compute_specs/vault_app/tests/`; check `test_Vault_App__Auto_DNS.py` for compositional pattern) | EXTENDED in phase 1a for stop/start state transitions |

### 2.2 Need to be built (NEW)

| Fixture | Phase | Where | Why |
|---------|-------|-------|-----|
| `Parameter__In_Memory` | 1b | `tests/unit/.../vault_publish/service/` or `sg_compute_specs/vault_publish/tests/fixtures/` | `Slug__Registry` uses `osbot_aws.helpers.Parameter`; we need a dict-backed subclass. **Check upstream osbot-aws first** — it may already ship one. If not, ~30-line wrapper. |
| `Route53__AWS__Client__In_Memory` | 1b | `tests/unit/sgraph_ai_service_playwright__cli/aws/dns/service/` | Composition for `Vault_Publish__Service` tests and bootstrap tests. Models the upsert/delete/get/list shape; tracks state in a dict keyed by `(zone, name, type)`. |
| `EC2_Instance__In_Memory` | 2c | `sg_compute_specs/vault_publish/tests/waker/fixtures/` | `Endpoint__Resolver__EC2` calls `EC2_Instance(id).{state,ip_address,start}`. Subclass with state-machine flips. |
| `CloudFront__AWS__Client__In_Memory` | 2a | `tests/unit/.../aws/cf/service/` | The full create/disable/delete state machine over an in-memory dict of distributions. |
| `Lambda__AWS__Client__In_Memory` | 2b | `tests/unit/.../aws/lambda_/service/` | Same for Lambdas + URLs. |
| `Lambda__Deployer__In_Memory` | 2b | Same | Deployer composes Deploy_Lambda upstream; in-memory variant records the build descriptor without actually packaging. |
| `ACM__AWS__Client__In_Memory` | 2d | `tests/unit/.../aws/acm/service/` | Just the read paths `find_by_domain`, `describe`. |
| Tiny inline HTTP server for `Endpoint__Proxy` | 2c | `sg_compute_specs/vault_publish/tests/waker/fixtures/inline_test_server.py` | Spawns a thread-bound `aiohttp` or `http.server` so the proxy hits real loopback (no mocks). |

---

## 3. The cross-phase composition pattern

Every `*_Service` test instantiates the real service class and injects in-memory clients:

```python
# example — sg_compute_specs/vault_publish/tests/test_Vault_Publish__Service.py
def test_register_writes_registry_and_creates_stack():
    registry = Slug__Registry      ().setup(parameter_client=Parameter__In_Memory())
    r53      = Route53__AWS__Client__In_Memory().setup()
    vault_app= Vault_App__Service  ().setup(aws_client=Vault_App__AWS__Client__In_Memory().setup())
    svc      = Vault_Publish__Service().setup(registry=registry, route53_client=r53, vault_app=vault_app)

    resp = svc.register(slug=Safe_Str__Slug('sara-cv'),
                        vault_key=Safe_Str__Vault__Key('vk-abc123'))

    assert resp.fqdn  == 'sara-cv.sg-compute.sgraph.ai'
    assert registry.get(Safe_Str__Slug('sara-cv')) is not None
    assert len(vault_app.aws_client.instance.calls('run_instance')) == 1
```

No `@patch`, no `MagicMock`. The test reads exactly like production code — that's the test-strategy invariant the codebase enforces.

---

## 4. CLI tests — golden-file

Pattern verified at `sg_compute_specs/vault_app/tests/test_Cli__Vault_App.py`. The test invokes the Typer app via `CliRunner` and asserts the output string matches a checked-in `.txt` snapshot. The snapshots live next to the test file as `expected/<verb>.txt`.

For `Cli__Vault_Publish`:

```
sg_compute_specs/vault_publish/tests/
├── test_Cli__Vault_Publish.py
└── expected/
    ├── register__sara_cv.txt
    ├── list__empty.txt
    ├── list__with_entries.txt
    ├── status__running.txt
    ├── status__stopped.txt
    ├── unpublish.txt
    └── bootstrap__dry_run.txt
```

Goldens use scrubbed timestamps / IDs (Type_Safe primitives can carry a `__deterministic_for_tests=True` mode if needed — verify the existing `Cli__Vault_App` test pattern).

---

## 5. Integration tests — real AWS, gated

Pattern verified at `tests/integration/sgraph_ai_service_playwright__cli/` (similar to `aws/dns/`). Gated by env vars:

| Env var | What it unlocks |
|---------|-----------------|
| `SG_AWS__DNS__ALLOW_MUTATIONS=1` | Route 53 mutations |
| `SG_VAULT_PUBLISH__ALLOW_MUTATIONS=1` | Spec-level mutations (`register`, `unpublish`, `bootstrap`) |
| `SG_AWS__CF__ALLOW_MUTATIONS=1` | CloudFront mutations (phase 2a / 2d) |
| `SG_AWS__LAMBDA__ALLOW_MUTATIONS=1` | Lambda mutations (phase 2b / 2d) |
| `SG_VAULT_PUBLISH__INTEGRATION=1` | Run the long bootstrap-then-register-then-cold-path tests (phase 2d) |

Integration tests are NEVER run in CI by default (per `library/docs/specs/v0.20.55__ci-pipeline.md` precedent). Operator runs them manually with credentials.

### 5.1 Acceptance test for phase 2d (the headline)

`tests/integration/sg_compute_specs/vault_publish/test_e2e__cold_path.py`:

1. `test_1__bootstrap` — invoke `bootstrap` with the test zone + cert ARN.
2. `test_2__register_slug` — `register('lab-e2e-<run-id>')`.
3. `test_3__stop_then_idle` — `vault-app stop`; assert DNS deleted; assert wildcard reachable.
4. `test_4__cold_request_returns_warming` — `curl` the FQDN; assert 200 + warming HTML.
5. `test_5__wait_for_running` — poll EC2 state; assert running within timeout.
6. `test_6__post_warm_lambda_drops_out_of_path` — `dig` after one TTL; assert specific A returned; second `curl` shows EC2 directly (no Lambda invocation in CloudWatch logs).
7. `test_7__teardown` — `unpublish`; assert clean.

Numbered top-down per CLAUDE.md testing rule #4.

---

## 6. What this plan does NOT test

Listed so Dev does not over-build:

- **No CloudFront real-distribution unit tests.** CF distribution lifecycle is ~30 min wall-clock; the in-memory client is the unit-test surface. The integration test in §5.1 covers the real path once per phase 2d push.
- **No Route 53 propagation tests.** That's the lab brief's territory (E10–E14). The vault-publish plan asserts the *API contract* (the right `change_id` lands), not the AWS-side timing.
- **No Lambda cold-start measurement.** Same — lab brief E30/E31.
- **No load tests.** Vault-publish is operator-paced; load testing belongs to the lab harness, if anywhere.
- **No mocks at all.** Worth restating.

---

## 7. CI footprint

| Phase | Unit tests in CI? | Integration tests in CI? |
|-------|-------------------|---------------------------|
| 1a | Yes — extended `Vault_App__AWS__Client__In_Memory` exercises stop/start | No |
| 1b | Yes — all in-memory | No |
| 2a | Yes | No (CF distribution churn is too expensive) |
| 2b | Yes | No (Lambda deploy churn) |
| 2c | Yes — Waker handler exercised against in-memory EC2 + inline HTTP server | No |
| 2d | Yes — bootstrap composed against in-memory CF/Lambda/ACM | No (the full e2e is operator-paced) |

CI workflow stays at unit-only. Dev runs integration manually after each phase via `pytest -m integration` with the appropriate env vars set.
