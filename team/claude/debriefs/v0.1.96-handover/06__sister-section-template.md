# 06 — Sister-Section Template

The proven shape from `sp os` (5a → 5i). `sp prom` and `sp vnc` follow the same 9-slice template. Each slice is its own commit; each has its own debrief.

## The template

| # | Slice | Files | Tests | Reference commit |
|---|---|---|---|---|
| **a** | Foundation | `__init__.py`, `primitives/Safe_Str__{X}__Stack__Name.py`, `primitives/Safe_Str__IP__Address.py`, `enums/Enum__{X}__Stack__State.py`, `service/{X}__AWS__Client.py` (skeleton with `{X}_NAMING` + 6 tag constants) | ~19 | `b0f3805` (sp os) / `1a19d3f` (sp prom) |
| **b** | Schemas + collections | 6 `Schema__{X}__*` files + `List__Schema__{X}__Stack__Info` collection + 1-2 section-specific primitives (e.g. `Safe_Str__OS__Password`) | ~19 | `9a1e04e` (sp os) |
| **c** | AWS helpers (4 small files) | `{X}__SG__Helper.py`, `{X}__AMI__Helper.py`, `{X}__Instance__Helper.py`, `{X}__Tags__Builder.py`. Update `{X}__AWS__Client.setup()` to wire all 4 + `Launch__Helper`. | ~22 | `f5dcde7` (sp os) |
| **d** | HTTP base + probe | `{X}__HTTP__Base.py` (request seam wrapping `requests` with `verify=False` + basic auth), `{X}__HTTP__Probe.py` (`cluster_health` + `ui_ready`) | ~14 | `05c0bb7` (sp os) |
| **e** | Service read paths + small helpers | `Caller__IP__Detector.py`, `Random__Stack__Name__Generator.py`, `{X}__Stack__Mapper.py`, `{X}__Service.py` with `setup()` + `list_stacks` / `get_stack_info` / `delete_stack` / `health` | ~33 | `82afd0e` (sp os) |
| **f.1** | User-data skeleton | `{X}__User_Data__Builder.py` with placeholder contract locked by test | ~6 | `363341c` (sp os) |
| **f.2** | Compose template | `{X}__Compose__Template.py` — service-specific docker-compose.yml renderer | ~9 | `8658520` (sp os) |
| **f.3** | User-data install steps | Expand `USER_DATA_TEMPLATE` with Docker install + compose-up + section-specific sysctls/setup | varies | `06bf140` (sp os) |
| **f.4a** | Launch helper | `{X}__Launch__Helper.py` — single-purpose `run_instance(...)` | ~11 | `0a09731` (sp os) |
| **f.4b** | Wire `create_stack` | `{X}__Service.create_stack(request, creator='')` composes all helpers + returns `Schema__{X}__Stack__Create__Response`. Update `{X}__AWS__Client.setup()` to also wire `launch`. | ~6 | `2b21126` (sp os) |
| **h** | FastAPI routes | `fast_api/routes/Routes__{X}__Stack.py` — 5 routes, zero logic in handlers | ~9 | `aef4018` (sp os) |
| **i** | Typer commands | `cli/Renderers.py` (Rich) + `scripts/{section}.py` (typer app) + mount in `provision_ec2.py` via `add_typer` (long form + short alias) | ~9 | `6abf20b` (sp os) |

## File-size budget

Per the operator's small-file discipline:

| File type | Target lines |
|---|---|
| Primitive | ≤ 25 |
| Enum | ≤ 25 |
| Schema | ≤ 50 |
| Collection | ≤ 15 |
| AWS helper (per concern) | ≤ 60 |
| HTTP base/probe | ≤ 50 each |
| Stack mapper | ≤ 60 |
| User-data builder | ≤ 80 |
| Compose template | ≤ 80 |
| Launch helper | ≤ 50 |
| Service orchestrator | ≤ 90 |
| FastAPI routes | ≤ 70 |
| Renderers | ≤ 100 |
| Typer commands | ≤ 90 |
| **Each test file** | ≤ 150 |

## Slice-by-slice TODO when starting a new section

1. **Pick the section name.** Folder name (long form) + typer aliases (long + short).
2. **Copy `cli/opensearch/primitives/Safe_Str__OS__Stack__Name.py` and `Enum__OS__Stack__State.py`** as the two parity-locked files. Run the parity tests; they verify regex + lifecycle vocabulary match across sister sections.
3. **Don't copy the `OpenSearch__AWS__Client` blindly** — bring just the skeleton + `{X}_NAMING` + tag constants. Helpers come in 6c.
4. **Mirror schemas only when needed.** `sp prom` has no admin password / no Dashboards URL — drop those fields. `sp vnc` adds `viewer_url` + interceptor selection.
5. **HTTP probes vary per section.** OS probes `/_cluster/health` + Dashboards `/`. `sp prom` probes `/-/healthy` + `/api/v1/targets`. `sp vnc` probes nginx 200 + mitmweb reachable.

## Tier-2A and Tier-2B duality

Service exposes pure-logic methods. Both Tier-2A (typer renderers) and Tier-2B (FastAPI routes) are thin wrappers:

```
sp os create [name]                      ← Tier-2A (typer + renderer)
                       ↘
                         OpenSearch__Service.create_stack(request)
                       ↗
POST /opensearch/stack                   ← Tier-2B (FastAPI route handler)
```

Same code path. Different output formats. No logic duplicated.
