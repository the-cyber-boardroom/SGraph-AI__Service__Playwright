# 04 — Implementation Phases

Both sections (`sp linux` and `sp docker`) are built in parallel phases.
Each phase ends with green tests; nothing is shipped half-finished to `dev`.

Version assignments:
- `v0.1.102` → `sp linux`
- `v0.1.103` → `sp docker`

---

## Shared pre-work (zero new code, just reading)

Before starting Phase 1, Dev should:
1. Read `sgraph_ai_service_playwright__cli/opensearch/service/OpenSearch__Service.py`
   — this is the exact pattern to follow (lazy `setup()`, modular helpers).
2. Read `sgraph_ai_service_playwright__cli/aws/Stack__Naming.py`.
3. Read `sgraph_ai_service_playwright__cli/elastic/service/Elastic__AWS__Client.py`
   lines 1–120 (tag constants + `ensure_instance_profile` + `resolve_latest_al2023_ami`).
4. Read `scripts/elastic.py` lines 1–120 (imports, app wiring, `resolve_stack_name`).

---

## Phase 1 — `sp linux` foundation (v0.1.102-a)

**Side-effect table:**

| File | Action |
|------|--------|
| `linux/__init__.py` | NEW (empty) |
| `linux/enums/Enum__Linux__Stack__State.py` | NEW |
| `linux/primitives/Safe_Str__Linux__Stack__Name.py` | NEW |
| `linux/schemas/Schema__Linux__*.py` (7 files) | NEW |
| `linux/service/Linux__Tags__Builder.py` | NEW |
| `linux/service/Linux__Stack__Mapper.py` | NEW |
| `linux/service/Linux__SG__Helper.py` | NEW (copies Elastic SG pattern) |
| `linux/service/Linux__Instance__Helper.py` | NEW (copies Elastic launch pattern) |
| `linux/service/Linux__AWS__Client.py` | NEW (composes SG + Instance helpers) |
| `linux/service/Linux__User_Data__Builder.py` | NEW (minimal cloud-init) |
| All `__init__.py` files | NEW (empty, CLAUDE.md rule 22) |
| Tests for all above | NEW |

**Demo / green tests:**

```python
def test_linux_aws_client_instantiates():
    c = Linux__AWS__Client()
    assert c.sg is not None
    assert c.instance is not None

def test_stack_mapper_roundtrip():
    # Build a fake describe_instances dict, assert all fields map correctly

def test_user_data_contains_auto_terminate_timer():
    ud = Linux__User_Data__Builder().render(stack_name='test', max_hours=2)
    assert 'systemd-run --on-active=2h' in ud

def test_user_data_no_timer_when_max_hours_zero():
    ud = Linux__User_Data__Builder().render(stack_name='test', max_hours=0)
    assert 'systemd-run' not in ud
```

---

## Phase 2 — `sp linux` service + CLI (v0.1.102-b)

**Side-effect table:**

| File | Action |
|------|--------|
| `linux/service/Linux__Health__Checker.py` | NEW |
| `linux/service/Linux__Service.py` | NEW |
| `linux/cli/__init__.py` | NEW |
| `linux/cli/Renderers.py` | NEW |
| `scripts/linux.py` | NEW |
| `scripts/provision_ec2.py` | MODIFY — mount linux_app |
| `fast_api/routes/Routes__Linux__Stack.py` | NEW |
| `fast_api/routes/` (registration) | MODIFY — register linux routes |
| Tests for all above | NEW |

**Demo / green tests:**

```python
def test_linux_service_create_wires_correctly():
    # In-memory: Linux__Service with fake AWS client
    # create() returns Schema__Linux__Create__Response with correct stack_name

def test_linux_service_list_returns_list_schema():
    # fake client returns 2 instances → list has 2 entries

def test_linux_service_delete_calls_terminate():
    # fake client records terminate call → delete response has instance_id

def test_linux_service_health_all_ok():
    # 4-check health with all fakes passing → all_ok=True

def test_route_create_returns_json():
    # Routes__Linux__Stack.Route__Linux__Stack__Create().handle(body).status_code == 200
```

**CLI smoke test** (not in CI — requires AWS):
```bash
sp linux create --wait --max-hours 1
sp linux list
sp linux health
sp linux exec -- "uname -a"
sp linux delete -y
```

---

## Phase 3 — `sp docker` foundation (v0.1.103-a)

Same structure as Phase 1 but for `docker/`.  Additional files:

| File | Action |
|------|--------|
| `docker/service/Docker__Compose__Template.py` | NEW |
| `docker/service/Docker__User_Data__Builder.py` | NEW (Docker install + optional image) |

**Key tests:**

```python
def test_docker_user_data_installs_docker():
    ud = Docker__User_Data__Builder().render(stack_name='test', max_hours=1)
    assert 'dnf install -y docker' in ud
    assert 'systemctl enable --now docker' in ud

def test_docker_user_data_pulls_image_when_provided():
    ud = Docker__User_Data__Builder().render(stack_name='t', max_hours=1,
                                              image='nginx:alpine', container_port=80)
    assert 'docker pull nginx:alpine' in ud
    assert '-p 80:80' in ud

def test_docker_user_data_no_image_when_empty():
    ud = Docker__User_Data__Builder().render(stack_name='t', max_hours=1)
    assert 'docker pull' not in ud

def test_compose_template_renders_valid_yaml():
    import yaml
    yml = Docker__Compose__Template().render(image='nginx:alpine', port=80)
    parsed = yaml.safe_load(yml)
    assert 'services' in parsed
```

---

## Phase 4 — `sp docker` service + CLI (v0.1.103-b)

Same structure as Phase 2 but for `docker/`.  Additional CLI commands:

```python
@docker_app.command('compose-ps')
def cmd_docker_compose_ps(name: Optional[str] = typer.Argument(None)):
    """Show running containers via `docker compose ps`."""
    # SSM exec: docker compose -f /opt/sg-docker/docker-compose.yml ps

@docker_app.command('compose-logs')
def cmd_docker_compose_logs(
    name : Optional[str] = typer.Argument(None),
    tail : int           = typer.Option(50, '--tail'),
):
    """Tail container logs via `docker compose logs`."""
    # SSM exec: docker compose logs --tail {tail}
```

Health checker adds 2 SSM-based checks (docker-daemon + containers-running).

**Demo / green tests** mirror Phase 2 but cover the extra checks and CLI commands.

---

## What NOT to build in v1

The following are explicitly out of scope for these two versions:

| Feature | Why deferred |
|---------|-------------|
| AMI baking (`sp linux ami create`) | Only useful after the core create/delete cycle is proven |
| `--from-ami` fast-launch path | Add once AMI workflow exists |
| `sp linux seed` / synthetic data | Not applicable for generic Linux |
| Kibana / dashboards | Not applicable |
| `sp docker compose-up --file` (external file) | v2; v1 uses `--image` or inline `compose_spec` |
| `--skip-processed` / LETS integration | Different concern entirely |
| FastAPI route for `exec` / `connect` | SSM interactive sessions can't go over HTTP |

---

## Test file layout

Tests mirror the source tree under `tests/unit/`:

```
tests/unit/sgraph_ai_service_playwright__cli/linux/
  enums/       test_Enum__Linux__Stack__State.py
  primitives/  test_Safe_Str__Linux__Stack__Name.py
  schemas/     test_Schema__Linux__Create__Request.py  (+ 6 more)
  service/     test_Linux__Tags__Builder.py
               test_Linux__Stack__Mapper.py
               test_Linux__User_Data__Builder.py
               test_Linux__Health__Checker.py
               test_Linux__Service.py

tests/unit/sgraph_ai_service_playwright__cli/docker/
  (same structure)
```

Each service test uses an in-memory subclass that overrides the real AWS
call.  No mocks — same pattern as `Linux__Service__In_Memory` seen in
OpenSearch tests.

---

## Estimated line counts

| Phase | New files | Approx lines | Copied from elastic/os |
|-------|-----------|--------------|------------------------|
| 1 (linux foundation) | ~14 | ~400 | ~65% |
| 2 (linux service+CLI) | ~6  | ~450 | ~55% |
| 3 (docker foundation) | ~15 | ~430 | ~70% of linux phase 1 |
| 4 (docker service+CLI)| ~6  | ~500 | ~60% of linux phase 2 |
| **Total** | **~41** | **~1800** | |
