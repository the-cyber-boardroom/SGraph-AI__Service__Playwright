# Reality — SP CLI / FastAPI Duality Refactor

**Status:** partial — read-only surface + delete mutation implemented.
Other mutation ops (create/backup/restore/dashboard-import/data-export/data-import) and CLI wrappers still PROPOSED.

This file tracks what exists today for the refactor proposed in
[`team/comms/briefs/v0.1.72__sp-cli-fastapi-duality.md`](../../../../comms/briefs/v0.1.72__sp-cli-fastapi-duality.md).
Everything in the brief that is NOT listed below is still PROPOSED.

---

## New top-level package — `sgraph_ai_service_playwright__cli/`

Sibling of `sgraph_ai_service_playwright/` and `agent_mitmproxy/`. Houses the
Type_Safe refactor of the `sp` / `ob` CLI. Nothing under
`sgraph_ai_service_playwright/` was modified. Package version: `v0.0.1`.

### `observability/` — Tier-1 pure-logic service (read-only surface)

| File | Role |
|------|------|
| `primitives/Safe_Str__Stack__Name.py` | AWS OS-domain-name compliant stack identifier (3-28 chars, lowercase, starts with letter). |
| `primitives/Safe_Str__AWS__Region.py` | AWS region code (MATCH regex). Empty allowed = resolve at runtime. |
| `primitives/Safe_Str__AWS__Endpoint.py` | AWS service endpoint hostname (no scheme). |
| `primitives/Safe_Int__Document__Count.py` | OS doc count; `-1` sentinel = not queried. |
| `enums/Enum__Stack__Component__Status.py` | Normalised lifecycle state across AMP/OS/AMG. |
| `enums/Enum__Stack__Component__Kind.py` | Identifies which AWS service a component represents. |
| `enums/Enum__Component__Delete__Outcome.py` | Per-component delete result code — DELETED / NOT_FOUND / FAILED. |
| `schemas/Schema__Stack__Component__AMP.py` | AMP workspace view. |
| `schemas/Schema__Stack__Component__OpenSearch.py` | OpenSearch domain view. |
| `schemas/Schema__Stack__Component__Grafana.py` | AMG workspace view. |
| `schemas/Schema__Stack__Info.py` | Aggregate stack view (AMP + OS + AMG; each nullable). |
| `schemas/Schema__Stack__List.py` | `list_stacks` response envelope (carries region). |
| `schemas/Schema__Stack__Component__Delete__Result.py` | Per-component delete outcome (kind + outcome + resource_id + error_message). |
| `schemas/Schema__Stack__Delete__Response.py` | `delete_stack` response envelope (name, region, results). |
| `collections/List__Stack__Info.py` | `Type_Safe__List` subclass for `Schema__Stack__Info`. |
| `collections/List__Stack__Component__Delete__Result.py` | `Type_Safe__List` subclass for delete results. |
| `service/Observability__AWS__Client.py` | Isolated boto3 + SigV4 boundary. **Only file in this package that imports boto3.** Methods: `amp_workspaces`, `opensearch_domains`, `amg_workspaces`, `opensearch_document_count`, `amp_delete_workspace`, `opensearch_delete_domain`, `amg_delete_workspace`. |
| `service/Observability__Service.py` | Pure logic: `list_stacks`, `get_stack_info`, `delete_stack`, `resolve_region`. |

### Tests (26 passing, 0 skipped)

| File | Coverage |
|------|----------|
| `tests/unit/sgraph_ai_service_playwright__cli/observability/primitives/test_Safe_Str__Stack__Name.py` | 7 cases — valid/invalid names, length boundaries, auto-init empty. |
| `tests/unit/.../primitives/test_Safe_Str__AWS__Region.py` | 3 cases — valid regions, empty allowed, bad shapes rejected. |
| `tests/unit/.../schemas/test_Schema__Stack__Info.py` | 4 cases — init, composition with components, JSON round-trip, `.obj()` coverage. |
| `tests/unit/.../service/Observability__AWS__Client__In_Memory.py` | In-memory test double (real subclass — no mocks). Fixture fields for listings + delete outcomes. |
| `tests/unit/.../service/test_Observability__Service.py` | 7 cases — list (populated + empty), get (populated / missing / endpoint-less), region resolution. |
| `tests/unit/.../service/test_Observability__Service__delete.py` | 5 cases — all deleted, all missing, partial-missing, forced failure, JSON round-trip. |

---

## What does NOT exist yet (still PROPOSED)

- CLI wrappers in the new package — typer `app` still lives in `scripts/observability.py` and `scripts/provision_ec2.py`. The new `delete_stack` service method is not yet wired to `ob delete`.
- Other mutation operations (`create`, `backup`, `restore`, `dashboard-import`, `data-export`, `data-import`).
- EC2 refactor (`Ec2__Service`) — provision_ec2.py at 2847 lines is untouched.
- FastAPI routes (`/v1/observability/*`).
- GH Actions workflows (`obs-morning.yml`, `obs-evening.yml`).

---

## Known tech-debt items

1. **boto3 usage** — `Observability__AWS__Client` imports boto3 directly, in violation of CLAUDE.md rule 8 (osbot-aws only). No osbot-aws wrapper exists for AMP / OpenSearch / Grafana services yet; the boundary is isolated to one file with a header comment flagging the exception. Swap to osbot-aws when wrappers land.
2. **Safe_Str primitive vs plain-dict key hash mismatch** — `Safe_Str__Stack__Name` has its own `__hash__`; lookups against plain-dict keys need a `str()` normalisation (see `Observability__Service.get_stack_info`). Consider replacing internal `Dict[str, …]` with a `Dict__*` collection subclass keyed by the Safe primitive so the cast disappears.
