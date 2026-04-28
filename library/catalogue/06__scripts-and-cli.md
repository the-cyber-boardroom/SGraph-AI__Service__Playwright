# 06 — Scripts and CLI

→ [Catalogue README](README.md)

All runnable entry points live in `scripts/`. The CLI is a Typer app hierarchy.
`scripts/run_sp_cli.py` is the top-level `sp` entry point.

---

## Scripts Inventory

| Script | Purpose |
|--------|---------|
| `scripts/elastic.py` | `sp el` — Elastic/Kibana stack CRUD + dashboard export/import + `sp el lets` mount |
| `scripts/elastic_lets.py` | `sp el lets cf` — inventory / events / consolidate / sg-send sub-commands |
| `scripts/observability.py` | `ob` — AMP + OpenSearch + Grafana stack list/info/delete |
| `scripts/observability_backup.py` | Backup tooling for observability stacks |
| `scripts/observability_opensearch.py` | OpenSearch-specific observability operations |
| `scripts/observability_utils.py` | Shared utilities for observability scripts |
| `scripts/opensearch.py` | `sp os` — OpenSearch EC2 stack lifecycle |
| `scripts/provision_ec2.py` | Direct EC2 provisioner for Playwright + sidecar stack (2847 lines; wraps into `Ec2__AWS__Client` helpers) |
| `scripts/provision_lambdas.py` | Provisions `sg-playwright-baseline-<stage>` + `sg-playwright-<stage>` Lambdas |
| `scripts/deploy_code.py` | S3 zip upload + `/admin/health` smoke test |
| `scripts/package_code.py` | Packages the code into a deployable zip |
| `scripts/run_sp_cli.py` | Top-level `sp` Typer app entry point |
| `scripts/sp-cli__run-locally.sh` | Shell convenience wrapper to run SP CLI locally |
| `scripts/__init__.py` | Package marker |

---

## `sp el` Typer Tree

```
sp el
    create [stack-name]          # Launch Elastic + Kibana EC2 stack
    list                         # List running stacks
    info [stack-name]            # Stack details
    delete [stack-name]          # Terminate stack
    dashboard
        export [stack-name]      # Export Kibana dashboard JSON
        import [stack-name]      # Import Kibana dashboard JSON
    lets
        cf
            inventory
                load             # Slice 1: S3 list → sg-cf-inventory-*
                wipe             # Delete inventory indices + dashboard
                list             # Recent run summaries
                health           # Cluster probe
            events
                load             # Slice 2: parse .gz → sg-cf-events-*
                wipe             # Delete events indices + reset manifest
                list             # Recent run summaries
                health           # Cluster probe
            consolidate
                load             # Slice 3: many .gz → events.ndjson.gz
            sg-send
                sync             # Slice 4: sync with SG_Send service
```

---

## `sp os` / `sp opensearch` Typer Tree

```
sp os (= sp opensearch)
    create [stack-name]          # Launch OpenSearch + Dashboards EC2 stack
    list                         # List stacks
    info [stack-name]            # Stack details
    delete [stack-name]          # Terminate stack
    health [stack-name]          # Cluster health probe
```

---

## `sp prom` / `sp prometheus` — PLANNED

Foundation only (Phase B step 6a). Typer commands not yet wired. See `02__cli-packages.md`.

---

## `ob` Observability Typer

```
ob
    list                         # List AMP + OpenSearch + Grafana stacks
    info [stack-name]            # Stack details
    delete [stack-name]          # Delete all components
```

CLI wrappers still live in `scripts/observability.py` — not yet moved into `__cli/`.

---

## CLI / FastAPI Duality

The SP CLI exposes the same operations as both:

1. **Typer commands** — for humans and shell scripts
2. **FastAPI routes** on `Fast_API__SP__CLI` — for GH Actions and programmatic callers

The stand-alone `Fast_API__SP__CLI` Lambda (`sp-playwright-cli-{stage}`) hosts both EC2 routes and Observability routes. OpenSearch routes are also mounted. See `02__cli-packages.md` for route details.

---

## Common CLI Flags (across `sp el lets cf` verbs)

| Flag | Meaning |
|------|---------|
| `--password P` | Elastic admin password (else `$SG_ELASTIC_PASSWORD`) |
| `--region R` | AWS region (else boto3 default chain) |
| `--dry-run` | Build queue, skip all writes |
| `--run-id ID` | Explicit run id (else auto-generated) |
| `[STACK_NAME]` | Auto-pick when only one stack exists; prompts on multiple |

---

## Cross-Links

- `02__cli-packages.md` — sub-package detail for each CLI section
- `03__lets-pipeline.md` — LETS pipeline commands in depth
- `04__elastic-stack.md` — `sp el` service layer
- `08__aws-and-infrastructure.md` — `provision_lambdas.py`, `provision_ec2.py`
