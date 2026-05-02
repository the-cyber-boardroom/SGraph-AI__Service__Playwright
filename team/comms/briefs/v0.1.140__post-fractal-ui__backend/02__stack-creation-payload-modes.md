# 02 — Stack-creation payload: three creation modes

## Goal

Extend the stack-creation request schema to support the three creation modes the 05/01 ephemeral-infra brief calls for, plus the AMI selector, instance size, and timeout fields the brief enumerates. This is the single largest schema-level change post-fractal-UI, and it gates ephemeral-infra features 2-10.

## Today

- The launch flow sends only `{ stack_name }` to the per-plugin create endpoint (e.g. `/firefox/stack`, `/podman/stack`, `/vnc/stack`). Verified at `sgraph_ai_service_playwright__api_site/components/sp-cli/sp-cli-launch-modal/v0/v0.1/v0.1.0/sp-cli-launch-modal.html` and the per-plugin-card `STATIC.create_endpoint_path` references.
- No `creation_mode`, no `ami_id`, no `instance_size`, no `timeout` field exists in any current request schema.
- Per-plugin create endpoints today take effectively `Schema__*__Stack__Create__Request` containing only a name + optional plugin-specific config.

## Required output

A unified stack-creation request envelope, applied uniformly across every per-plugin create endpoint (or a base schema that each plugin extends).

### Contract — `Schema__Stack__Create__Request__Base`

```python
class Schema__Stack__Create__Request__Base(Type_Safe):
    stack_name      : Safe_Str__Stack__Name | None        # auto-generated if None
    creation_mode   : Enum__Stack__Creation_Mode          # FRESH / BAKE_AMI / FROM_AMI
    ami_id          : Safe_Str__AWS__AMI_Id | None        # required when creation_mode=FROM_AMI
    instance_size   : Enum__Instance__Size | None         # SMALL / MEDIUM / LARGE — service maps to AWS instance type
    timeout_minutes : Safe_Int__Timeout__Minutes | None   # ephemeral-infra brief: required for auto-terminate
```

Per-plugin schemas extend this base and add plugin-specific config (e.g. firefox adds credentials handle, MITM script handle).

### Contract — `Enum__Stack__Creation_Mode`

```python
class Enum__Stack__Creation_Mode(Enum):
    FRESH    = 'fresh'      # cold-boot from base AMI, run user-data
    BAKE_AMI = 'bake-ami'   # cold-boot, then snapshot the result as a new AMI
    FROM_AMI = 'from-ami'   # boot from a pre-baked AMI (no user-data)
```

### Validation rules (in `Request__Validator`)

- `creation_mode == FROM_AMI` → `ami_id` MUST be present.
- `creation_mode != FROM_AMI` → `ami_id` MUST be absent.
- `creation_mode == BAKE_AMI` → service emits an AMI bake activity entry (consumed by `sp-cli-activity-pane`).
- `timeout_minutes` defaults per plugin (firefox 60, podman 60, vnc 30) — defaults live with the plugin, not in the base schema.
- `instance_size` defaults per plugin via `Capability__Detector`.

### Response

Existing per-plugin response shape preserved. Add one optional field:

```python
class Schema__Stack__Create__Response(Type_Safe):
    # ... existing fields ...
    bake_status : Schema__AMI__Bake__Status | None        # populated only when creation_mode=BAKE_AMI
```

`Schema__AMI__Bake__Status` exposes `state` (BAKING / READY / FAILED), `target_ami_id` (when ready), and `started_at`.

### Acceptance criteria

- One Type_Safe class per file. New enum file `Enum__Stack__Creation_Mode.py`. New base schema file. Existing per-plugin schemas extend the base.
- `Request__Validator` carries the cross-field rules.
- Each per-plugin create route accepts the new envelope; default values match the per-plugin defaults documented above.
- Integration tests: one per creation mode per plugin (matrix). FROM_AMI tests assert that user-data does NOT run.
- Reality doc shard updated.

## Open questions

1. **AMI ownership.** Does the AMI registry live in `osbot-aws` only, or do we expose `/ami/list` to feed the UI's AMI picker? See ephemeral-infra brief feature 3 — likely a sibling endpoint, but out of scope for THIS brief.
2. **`instance_size` mapping.** The ephemeral-infra brief implies T-shirt sizes; AWS instance types are the underlying thing. Mapping table lives where — `Capability__Detector` per plugin, or a central `Instance__Size__Catalog`?
3. **BAKE_AMI cost surface.** Bake takes minutes and incurs storage cost. Does the response stream progress (SSE / websocket), or is it a poll-the-bake-status endpoint? Recommendation: poll `/ami/bake/{stack_id}/status`. Architect call.
4. **Idempotency.** If the UI retries a launch, do we collide on `stack_name`? Today's behaviour vs new behaviour should be confirmed.

## Out of scope

- AMI listing, bake-status polling endpoint, AMI deletion. These are sibling topics under the ephemeral-infra umbrella.
- Sidecar attachment payload (container-runtime brief). Will be a separate request schema.

## Paired-with

- Frontend consumer: `../v0.1.140__post-fractal-ui__frontend/02__launch-flow-three-modes.md`.
- Source: `team/humans/dinis_cruz/briefs/05/01/v0.22.19__dev-brief__ephemeral-infra-next-phase.md`.
