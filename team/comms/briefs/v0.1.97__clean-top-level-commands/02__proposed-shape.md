# Proposed shape — `sp` after the v0.1.97 cleanup

## Top level — only global / cross-cutting ops

```
sp catalog                          # Enumerate all stacks across all sections (mirrors GET /catalog/stacks)
sp doctor                           # Global preflight — account, region, ECR access, IAM passrole, etc.
sp --version
sp --help
```

That's it at the top level. Three commands + the standard typer flags. Everything else is in a subgroup.

## Stack subgroups — each section symmetric

Every stack type gets the same shape. The new `sp pw` joins the existing sisters.

| Long form | Short alias | Scope |
|---|---|---|
| `sp playwright`  | `sp pw`  | Playwright + agent-mitmproxy stack (the headless API) |
| `sp elastic`     | `sp el`  | Elasticsearch + Kibana |
| `sp opensearch`  | `sp os`  | OpenSearch + Dashboards |
| `sp prometheus`  | `sp prom`| Prometheus + cAdvisor + node-exporter |
| `sp vnc`         | —        | Browser-viewer (chromium + nginx + mitmproxy) |
| `sp linux`       | `sp lx`  | Bare AL2023 EC2 |
| `sp docker`      | `sp dk`  | AL2023 + Docker CE EC2 |
| `sp observability` | `sp ob`| AMP + AMG + OpenSearch managed services |

All eight follow the same command shape (where applicable):

```
sp <section> create [name] [--region] [--instance-type] [<section-specific flags>]
sp <section> list                   [--region]
sp <section> info <name>            [--region]
sp <section> delete <name>          [--region]
sp <section> connect <name>         [--region]                   # SSM shell on host
sp <section> shell <name> [--container]   [--region]             # SSM shell inside container
sp <section> forward <name> [--port]      [--region]             # SSM port-forward
sp <section> health <name>                [--region]
sp <section> wait <name>                  [--region]
sp <section> ami {create, wait, tag, list}                        # AMI lifecycle, scoped to this section
```

## What moves under `sp pw`

The 21 currently-top-level commands become subcommands of `sp pw`. Verbatim — same flags, same behaviour, same renderers:

```
sp pw create / list / info / delete / connect / shell / env / run /
   exec / exec-c / logs / diagnose / forward / wait / clean /
   create-from-ami / open / screenshot / smoke / health / ensure-passrole
```

Plus the existing `sp vault` and `sp ami` subgroups move under `sp pw`:

```
sp pw vault {clone, list, run, commit, push, pull, status}
sp pw ami   {create, wait, tag, list}
```

`sp create-from-ami` becomes `sp pw create-from-ami` (kept at the section's top level — different action from the AMI-lifecycle verbs, mirrors `sp el create-from-ami`).

## What lands at the top — and why

### `sp catalog`

Mirrors `GET /catalog/types` and `GET /catalog/stacks` from the FastAPI surface. Two subcommands:

```
sp catalog types              # List all known stack types + their per-type metadata
sp catalog stacks [--type X]  # Cross-section list of live stacks (Linux + Docker + Elastic + …)
```

Currently the only way to see a cross-section view is via the API or by running `sp linux list` / `sp docker list` / etc. one at a time. `sp catalog stacks` collapses that into a single command.

### `sp doctor`

Replaces `sp ensure-passrole` and absorbs the preflight checks scattered across the existing top level. Three subcommands:

```
sp doctor                     # Run all checks; exit 0 if green
sp doctor passrole            # Just the iam:PassRole check (current sp ensure-passrole)
sp doctor preflight           # AWS account / region / ECR access / image presence
```

Section-specific preflights (`sp pw doctor` etc.) can be added later as each section grows them; the cross-section doctor handles the global stuff.

## What `sp --help` looks like after

```
Usage: sp [OPTIONS] COMMAND [ARGS]...

Manage ephemeral EC2 stacks for the SG/Send ecosystem.

Commands:
  catalog                    Enumerate all live stacks across all sections.
  doctor                     Run preflight checks (AWS account, region, ECR, IAM).

Subgroups:
  pw      (playwright)       Playwright + agent-mitmproxy stack.
  el      (elastic)          Elasticsearch + Kibana.
  os      (opensearch)       OpenSearch + Dashboards.
  prom    (prometheus)       Prometheus + cAdvisor + node-exporter.
  vnc                        Browser-viewer (chromium + nginx + mitmproxy).
  linux   (lx)               Bare AL2023 EC2.
  docker  (dk)               AL2023 + Docker CE EC2.
  ob      (observability)    AMP + AMG + OpenSearch managed.
```

Two top-level commands + 8 subgroups (each with a short alias). Symmetric. Predictable.

## What disappears

| Was | Why | Replacement |
|---|---|---|
| `sp create` | Playwright-specific | `sp pw create` |
| `sp list` | Playwright-specific | `sp pw list` (and `sp catalog stacks` for cross-section) |
| `sp ensure-passrole` | One specific preflight | `sp doctor passrole` |
| `sp ami create` | Playwright-AMI-specific | `sp pw ami create` |
| `sp vault clone` | Playwright-EC2-vault-specific | `sp pw vault clone` |
| (every other top-level command) | Playwright-specific | `sp pw <same-name>` |

## Trade-offs

- **Plus:** symmetry; one mental model; UI driven from `/catalog/stacks` matches CLI shape; easier to add future stack types.
- **Plus:** scope of every command becomes obvious from the prefix.
- **Minus:** hard cut breaks every operator's typing muscle memory.
- **Minus:** runbook updates required.
- **Minus:** `sp pw` is two extra characters to type for the most common path.
