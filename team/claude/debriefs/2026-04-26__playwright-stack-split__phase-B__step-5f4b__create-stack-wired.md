# Phase B · Step 5f.4b — Wire `create_stack` into `OpenSearch__Service`

**Date:** 2026-04-26.
**Commit:** `2b21126`.
**Plan:** `team/comms/plans/v0.1.96__playwright-stack-split/04__sp-os__opensearch.md`.
**Predecessor:** Step 5f.4a (launch helper).

---

## What shipped

End-to-end `sp os create_stack` working in pure logic. The Service composes every helper landed in 5a–5f.4a.

`OpenSearch__AWS__Client` gains a 5th slot:
- `launch : OpenSearch__Launch__Helper` (lazy via `setup()`)

`OpenSearch__Service` gains:
- 2 new slots — `compose_template` + `user_data_builder` (lazy)
- `create_stack(request, creator='') -> Schema__OS__Stack__Create__Response`

### Default resolution flow

| Field | Empty → resolution |
|---|---|
| `stack_name` | `'os-{adjective}-{scientist}'` via `name_gen` |
| `region` | `DEFAULT_REGION` (`'eu-west-2'`) |
| `caller_ip` | `ip_detector.detect()` |
| `admin_password` | `secrets.token_urlsafe(PASSWORD_BYTES=24)` ⇒ 32-char URL-safe base64 (fits `Safe_Str__OS__Password` 16-64 regex) |
| `from_ami` | `ami.latest_al2023_ami_id(region)` |
| `instance_type` | `'t3.large'` |

### Composition

```
sg.ensure_security_group(region, stack_name, caller_ip)         → sg_id
tags.build(stack_name, caller_ip, creator)                      → tags
compose_template.render(admin_password=password)                → compose_yaml  ← secret only here
user_data_builder.render(stack_name, region, compose_yaml)      → user_data     ← does NOT take admin_password
launch.run_instance(region, ami_id, sg_id, user_data, tags, …)  → instance_id
```

Returns `Schema__OS__Stack__Create__Response(state=PENDING, ...)` with `aws_name_tag` built via `OS_NAMING.aws_name_for_stack(stack_name)`.

## Tests

6 new `create_stack` tests with real `_Fake_*` subclasses (no mocks):
- Empty request resolves all defaults (name `'os-{gen}'`, default region, detector IP, generated password, latest AL2023, default instance type, PENDING)
- Request overrides take priority — when fields set, AMI helper / IP detector / name generator are NOT called (defensive; asserted via `.calls == []`)
- Compose password flows into user-data via compose only — user-data builder signature does not take `admin_password`
- SG ingress uses resolved `caller_ip`
- Launch call carries correct user_data marker, AMI, SG, tags

`setup()` chain extended to wire 7 helpers; AWS client wires 5.

## Files changed

```
M  sgraph_ai_service_playwright__cli/opensearch/service/OpenSearch__Service.py
M  sgraph_ai_service_playwright__cli/opensearch/service/OpenSearch__AWS__Client.py
M  tests/unit/sgraph_ai_service_playwright__cli/opensearch/service/test_OpenSearch__Service.py
M  tests/unit/sgraph_ai_service_playwright__cli/opensearch/service/test_OpenSearch__AWS__Client.py
M  team/roles/librarian/reality/v0.1.31/06__sp-cli-duality-refactor.md
```
