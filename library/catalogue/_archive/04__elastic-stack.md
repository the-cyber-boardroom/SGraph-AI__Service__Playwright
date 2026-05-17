# 04 — Elastic / Kibana Stack

→ [Catalogue README](README.md)

Manages ephemeral single-node Elastic + Kibana stacks on EC2.
Accessed via `sp el` CLI verbs and the Elastic HTTP client used by the LETS pipeline.

---

## Stack Service Layer

`sgraph_ai_service_playwright__cli/elastic/service/`

| Class | Role |
|-------|------|
| `Elastic__Service.py` | Tier-1 orchestrator: `create_stack`, `list_stacks`, `get_stack_info`, `delete_stack` |
| `Elastic__AWS__Client.py` | AWS boundary (EC2 + IAM + SG). Declares `ELASTIC_NAMING = Stack__Naming(section_prefix='elastic')`. Methods: `ensure_security_group`, `latest_al2023_ami_id`, `launch_instance`, `terminate_instance`. |
| `Elastic__HTTP__Client.py` | Elasticsearch HTTP boundary (bulk-post, delete-by-pattern, count, aggregate). See ES optimisations below. |
| `Kibana__Saved_Objects__Client.py` | Kibana API: `ensure_data_view`, `import_objects`, `export_objects`, `find`, `delete`. |
| `Elastic__User__Data__Builder.py` | Renders EC2 UserData bash (installs Docker, pulls image, runs Elastic + Kibana). |
| `Default__Dashboard__Generator.py` | Generates a default Kibana dashboard ndjson. |
| `Synthetic__Data__Generator.py` | Generates synthetic ES documents for testing. |
| `Caller__IP__Detector.py` | Fetches caller's public IPv4 (for SG ingress rules). |
| `AWS__Error__Translator.py` | Maps AWS error codes to human-readable messages. |
| `Kibana__Disabled_Features.py` | Constants for disabling Kibana features in the stack. |

---

## Elastic Schemas and Enums

`sgraph_ai_service_playwright__cli/elastic/`

| Layer | Key types |
|-------|-----------|
| enums | `Enum__Elastic__State` (PENDING/RUNNING/READY/TERMINATING/TERMINATED/UNKNOWN) |
| primitives | `Safe_Str__Elastic__Stack__Name`, `Safe_Str__Elastic__Password`, `Safe_Str__Kibana__Url`, etc. |
| schemas | `Schema__Elastic__Stack__Create__Request`, `Schema__Elastic__Stack__Info`, `Schema__Elastic__Stack__Delete__Response`, etc. |

---

## `Inventory__HTTP__Client` — 7 ES Optimisations

Used by LETS pipeline slices 1–3. Seven opt-in improvements added in the consolidate slice:

| ID | Optimisation | Default |
|----|-------------|---------|
| E-1 | `refresh` param on `bulk_post_with_id` | `True` |
| E-2 | `routing` param on `bulk_post_with_id` | `''` |
| E-3 | `requests.Session()` keep-alive | On by default |
| E-4 | `ensure_index_template()` method | N/A (new method) |
| E-5 | Auto-split bulk payloads by `max_bytes` | `0` (disabled) |
| E-6 | `update_by_query_terms()` batch update | N/A (new method) |
| E-7 | `wait_for_active_shards` param | `'null'` (ES default) |

`Inventory__HTTP__Client` lives in `elastic/lets/cf/inventory/service/`.

---

## Kibana Dashboard Pattern

- Slice 1 auto-imports a 5-panel dashboard (`sg-cf-inventory-overview`) using Vis Editor saved-objects.
- Slice 2 auto-imports a 6-panel dashboard (`sg-cf-events-overview`).
- **Vis Editor (not Lens)** is used for auto-imported dashboards — avoids Kibana migration footguns.
- UI-built Lens dashboards round-trip via `sp el dashboard export` / `sp el dashboard import`.

---

## LETS Index Patterns

| Index | Data view | Time field |
|-------|-----------|-----------|
| `sg-cf-inventory-{YYYY-MM-DD}` | `sg-cf-inventory-*` | `delivery_at` |
| `sg-cf-events-{YYYY-MM-DD}` | `sg-cf-events-*` | `timestamp` |
| `sg-cf-consolidated-{YYYY-MM-DD}` | (manifest docs) | `loaded_at` |
| `sg-pipeline-runs-{YYYY-MM-DD}` | (journal docs) | `loaded_at` |

---

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/elastic.py` | Main `sp el` Typer app — stack CRUD + dashboard export/import |
| `scripts/elastic_lets.py` | `sp el lets cf` sub-tree — inventory / events / consolidate / sg-send |

---

## Tests

- 165 elastic-service unit tests under `tests/unit/sgraph_ai_service_playwright__cli/elastic/service/`
- LETS tests are in their own subtrees (see `07__testing-patterns.md`)
- All use `Elastic__AWS__Client__In_Memory` and `Kibana__Saved_Objects__Client__In_Memory` — no mocks

---

## Cross-Links

- `03__lets-pipeline.md` — LETS pipeline layered on top of this stack
- `06__scripts-and-cli.md` — CLI entry points (`sp el` verbs)
- `team/roles/librarian/reality/v0.1.31/10__lets-cf-inventory.md` — slice 1 canonical reality
