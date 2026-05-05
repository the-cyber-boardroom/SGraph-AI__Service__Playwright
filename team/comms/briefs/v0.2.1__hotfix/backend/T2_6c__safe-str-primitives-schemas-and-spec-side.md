# T2.6c — Safe_* primitives: schema fields + spec-side service sweep

⚠ **PARTIAL follow-on from T2.6b.** T2.6b typed public method signatures on Pod__Manager, Platform, EC2__Platform and wired Safe_Str wrapping in Routes__Compute__Pods and Routes__Compute__Nodes. Two areas intentionally deferred here.

## What T2.6b left untyped

### 1. Pod schema field primitives

These schema classes in `sg_compute/core/pod/schemas/` carry raw `: str` / `: int` field types:

| File | Raw fields |
|------|-----------|
| `Schema__Pod__Info.py` | `pod_name: str`, `node_id: str`, `image: str`, `ports: str` |
| `Schema__Pod__Stats.py` | `container: str` |
| `Schema__Pod__Logs__Response.py` | `container: str`, `content: str` |
| `Schema__Pod__Stop__Response.py` | `name: str`, `error: str` |
| `Schema__Pod__Start__Request.py` | `name: str`, `image: str`, `type_id: str` |

New primitives needed (none exist yet):
- `Safe_Str__Container__Name` (for `container`, `name` fields in stats/stop/logs) — or alias `Safe_Str__Pod__Name`?
- `Safe_Str__Docker__Image` (for `image` fields, e.g. `nginx:latest`) — note: colons and slashes are valid in image refs; the regex must be permissive
- `Safe_Str__Port__Map` (for `ports` string, which is Docker port-mapping format, e.g. `0.0.0.0:8080->80/tcp`)
- `Safe_Str__Log__Content` (for `content` — arbitrary multi-line log text; probably just allow_empty=True with no regex)
- `Safe_Str__Spec__Type_Id` (for `type_id` — may already exist in vault primitives)
- `Safe_Int__Log__Lines` (for `lines`)

**Architect input needed:** Some of these (log content, port map) are wide-open strings. Is `Safe_Str__Message` acceptable as a catch-all, or do we need purpose-specific primitives? The precedent in BV2.x used purpose-specific names.

Also: `Sidecar__Client` class fields `host_api_url: str` and `api_key: str` — `host_api_url` is an internal HTTP client base URL (not a schema field); `api_key` is a secret. Both are internal helper attributes. Decide whether these warrant primitives or are exempt as infrastructure glue.

### 2. Spec-side service class sweep

`sg_compute_specs/<spec>/service/` files still carry raw `: str` / `: int` on their render/build methods:

| Spec | File | Raw params |
|------|------|-----------|
| docker | `Docker__User_Data__Builder.render` | `stack_name: str`, `region: str`, `registry: str`, `api_key_name: str`, `api_key_ssm_path: str`, `max_hours: int` |
| docker | `Docker__Service.create_node` | `api_key_ssm_path: str` |
| docker | `Docker__Service.list_stacks/get_stack_info/delete_stack` | `region: str`, `stack_name: str` |
| firefox | `Firefox__Launch__Helper.run_instance` | `region: str`, `ami_id: str`, `sg_id: str`, `user_data: str`, `instance_type: str` |
| vnc | (similar — not fully enumerated) | |
| podman | (similar — not fully enumerated) | |

Note: `Docker__Instance__Helper`, `Docker__SG__Helper`, `Docker__Launch__Helper`, `Firefox__SG__Helper` etc. are infrastructure helper classes (wrap boto3). Per T2.6b brief rule: "Internal helpers can use raw types." These are exempt.

The `Docker__Service` public-facing verbs and `*__User_Data__Builder.render()` are the actual scope here.

## Architect question before starting

Does `api_key_ssm_path: str` → `Safe_Str__SSM__Path`? The primitive exists. But it travels from EC2__Platform down to per-spec service `create_node` methods. Confirm this substitution is wanted before sweeping all spec services.

## Acceptance criteria (T2.6c)

- All schema fields in `sg_compute/core/pod/schemas/` use primitives (or justified exceptions agreed with Architect).
- `Docker__Service`, `Podman__Service`, `Vnc__Service` public methods typed.
- `*__User_Data__Builder.render()` parameters typed where a primitive exists.
- `grep -rn ': str' sg_compute/core/pod/schemas/` → zero hits.

## Source

T2.6b debrief, T2.6b code review (2026-05-05 14:00).
