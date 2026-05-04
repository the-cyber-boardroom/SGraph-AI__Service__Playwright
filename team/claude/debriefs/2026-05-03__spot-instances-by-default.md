# Debrief — Spot instances by default across all EC2 stacks

**Date:** 2026-05-03
**Commits:** 16afcde, e8a79e8
**Branch:** `claude/sg-compute-b4-control-plane-xbI4j`

---

## What was built

Spot instances are now the default for every EC2 stack the CLI can create
(docker, podman, vnc, firefox, neko, prometheus, opensearch). On-demand is
opt-out via `--no-spot`.

```
sp docker create --wait          # spot (default)
sp docker create --no-spot --wait  # on-demand
sp firefox create-from-ami --no-spot  # create-from-ami also covered
```

Pricing is now visible in all three docker output surfaces:

```
sp docker list   → 'pricing' column: spot (cyan) | on-demand (dim)
sp docker info   → 'pricing' row
sp docker create → 'pricing' line in create output
```

---

## Files changed

### AWS API layer — 7 Launch Helpers
Each gained `use_spot: bool = True` and:
```python
if use_spot:
    kwargs['InstanceMarketOptions'] = {'MarketType': 'spot'}
```
- `Docker__Launch__Helper`, `Podman__Launch__Helper`, `Vnc__Launch__Helper`
- `Firefox__Launch__Helper`, `Neko__Launch__Helper`
- `Prometheus__Launch__Helper`, `OpenSearch__Launch__Helper`

Firefox already had `max_hours` in the signature; `use_spot` appended after it.

### Schemas — 7 create request schemas
`use_spot: bool = True` added to each:
- `Schema__Docker__Create__Request`, `Schema__Podman__Create__Request`
- `Schema__Vnc__Stack__Create__Request`, `Schema__Firefox__Stack__Create__Request`
- `Schema__Neko__Stack__Create__Request`
- `Schema__Prom__Stack__Create__Request`, `Schema__OS__Stack__Create__Request`

### Services — 8 run_instance call sites
`use_spot=request.use_spot` threaded through. Firefox has two call sites
(create + create_from_ami).

### CLI scripts — 9 create commands
`--no-spot: bool = typer.Option(False, '--no-spot', ...)` added.
`use_spot = not no_spot` passed to the request schema.
- `scripts/docker_stack.py` (create)
- `scripts/podman.py` (create)
- `scripts/vnc.py` (create)
- `scripts/prometheus.py` (create)
- `scripts/opensearch.py` (create)
- `sgraph_ai_service_playwright__cli/neko/cli/__init__.py` (create)
- `sgraph_ai_service_playwright__cli/firefox/cli/__init__.py` (create + create-from-ami)

### Docker display layer
- `Schema__Docker__Info`: `spot: bool = False`
- `Docker__Stack__Mapper.to_info()`: `spot = details.get('InstanceLifecycle', '') == 'spot'`
- `Schema__Docker__Create__Response`: `use_spot: bool = True`
- `Docker__Service.create_stack`: `use_spot=request.use_spot` in return
- `Renderers.py`: `_spot_label()` helper; pricing column in list; pricing row in info and create

### Tests — 5 fake launch helper stubs updated
`_Fake_Launch.run_instance()` in:
- `test_Stack__Events.py` (event bus — shared across docker/podman/vnc/neko/elastic)
- `test_Vnc__Service.py`, `test_Prometheus__Service.py`, `test_OpenSearch__Service.py`
- `test_Firefox__Plugin.py`, `test_Neko__Plugin.py`

Two new assertions in `test_Prometheus__Launch__Helper.py`:
- `test_run_instance__spot_market_options_sent_by_default`
- `test_run_instance__no_spot_omits_market_options`

Total: 35 files changed, 90 insertions, 30 deletions. 1636 unit tests passing.

---

## Failure analysis

### Bad failure — `_Fake_Launch` stubs not updated in two passes

The `_Fake_SG.ensure_security_group` stub in `test_Stack__Events.py` was
already missing `open_to_all` from the prior host-control-plane work.
When `use_spot` was added to `run_instance`, the same pattern repeated
across five test files in a second pass.

**Root cause:** Fake collaborators in tests mirror the real interface but
have no enforcement mechanism — when the real signature grows, the fakes
silently drift until a test runs. This is a structural gap, not a one-off.

**Mitigation:** The pattern is now visible. Future Launch Helper signature
changes should grep for `def run_instance` across `tests/` immediately and
update all stubs in the same commit.

### Good failure — AWS `AuthFailure.ServiceLinkedRoleCreationNotPermitted`

```
ClientError: An error occurred (AuthFailure.ServiceLinkedRoleCreationNotPermitted)
when calling the RunInstances operation: The provided credentials do not have
permission to create the service-linked role for EC2 Spot Instances.
```

**Root cause:** AWS requires the account-level role `AWSServiceRoleForEC2Spot`
to exist before any spot `RunInstances` call is accepted. It is auto-created
on first use — but only if the caller has `iam:CreateServiceLinkedRole`. The
CLI credentials do not have that permission.

**Fix (one-time per AWS account):**
```bash
aws iam create-service-linked-role --aws-service-name spot.amazonaws.com
```

This is a good failure: it surfaced immediately on first real `sp docker create`
with spot enabled, the error message is unambiguous, and the fix is a single
command with no code change required.

**Future hardening (not done):** The CLI could detect this error and print the
`aws iam create-service-linked-role` command as a hint, rather than surfacing
the raw AWS error. Low priority — operators only see this once per account.

---

## Design decision — default ON, not opt-in

All ephemeral stacks in this system are designed to be stateless and
short-lived. Spot interruption (2-minute notice) is acceptable for all current
workloads (Docker, Podman, Firefox, VNC, Prometheus, OpenSearch). Typical
cost saving is 60–70% vs on-demand for `t3.*` families.

The decision to make `--no-spot` the opt-out (rather than `--spot` the opt-in)
is intentional: operators who forget the flag get the cheaper option by default,
and the label is visible in every output surface so the choice is never invisible.

Interruption handling (responding to the 2-minute notice, re-launching on a new
instance, draining state) is noted as a future concern and explicitly out of scope
for this slice.

---

## What does not exist yet (PROPOSED)

- **Spot interruption handler** — cloud-init or systemd unit that listens to
  `http://169.254.169.254/latest/meta-data/spot/instance-action` and triggers
  a graceful shutdown or re-launch. PROPOSED — does not exist yet.
- **Spot price cap** — `SpotOptions.MaxPrice` is not set; the current behaviour
  uses the on-demand price as the ceiling. PROPOSED — does not exist yet.
- **Pre-flight check for `AWSServiceRoleForEC2Spot`** — the CLI currently lets
  the raw AWS error surface. A `sp doctor` or `--no-spot` fallback hint would
  improve first-run UX. PROPOSED — does not exist yet.
- **Spot display for non-docker specs** — only `sp docker list/info/create`
  show the pricing label. Podman, VNC, Firefox, Neko, Prometheus, OpenSearch
  list/info renderers do not yet show spot status. PROPOSED — does not exist yet.
