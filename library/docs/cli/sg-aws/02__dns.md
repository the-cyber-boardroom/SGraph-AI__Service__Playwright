---
title: "sg aws dns — Route 53 commands"
file: 02__dns.md
author: Architect (Claude)
date: 2026-05-17
parent: README.md
---

# 02 — `sg aws dns`

Route 53 hosted-zone, record, and propagation management. Subcommand groups:

| Group | Alias | What it does |
|-------|-------|--------------|
| `zones` | — | Account-wide hosted-zone listing |
| `zone` | `z` | One-zone operations (show, list, check, purge) |
| `records` | `r` | Record-level CRUD + propagation checks |
| `instance` | `i` | DNS↔EC2-instance helpers |

**Default zone:** `sg-compute.sgraph.ai`. Override with `SG_AWS__DNS__DEFAULT_ZONE` or the `--zone`/`-z` flag.

**Mutation gate:** `SG_AWS__DNS__ALLOW_MUTATIONS=1` required for any `add`, `update`, `delete`, `purge`, or `instance create-record`.

---

## `zones` — account-wide

### `sg aws dns zones list`

List every hosted zone in the account.

```bash
sg aws dns zones list
sg aws dns zones list --json
```

---

## `zone` (alias `z`) — one zone at a time

All `zone` verbs accept a positional zone name or ID. Omitted → default zone.

### `sg aws dns zone show [name|id]`

Zone metadata: ID, name, comment, NS set, record count.

```bash
sg aws dns zone show
sg aws dns zone show sg-compute.sgraph.ai
sg aws dns z show --json
```

### `sg aws dns zone list [name|id]`

Every DNS record in the zone, with type, TTL, value.

```bash
sg aws dns zone list
sg aws dns z list --json | jq '.records[] | select(.type=="A")'
```

### `sg aws dns zone check [name|id]`

Health-check every A record. Classifies each as `OK`, `ORPHANED` (points at an IP/instance that no longer exists), or `STALE` (points at a stopped instance, etc.).

```bash
sg aws dns zone check
sg aws dns zone check --json
```

Use the output to decide whether `zone purge` is safe.

### `sg aws dns zone purge [name|id]`  ⚠ mutates

Delete A records classified as ORPHANED and/or STALE by `zone check`.

```bash
# always look first
sg aws dns zone check

# then purge with --dry-run
SG_AWS__DNS__ALLOW_MUTATIONS=1 sg aws dns zone purge --dry-run

# then for real
SG_AWS__DNS__ALLOW_MUTATIONS=1 sg aws dns zone purge --yes --wait
```

**Flags:**
- `--only {orphaned|stale}` — restrict the purge category
- `--dry-run` — show what would be deleted, do nothing
- `--yes` — skip confirmation
- `--wait` — block until each `ChangeBatch` reaches INSYNC
- `--wait-timeout N` — INSYNC poll budget per change (seconds)
- `--json`

---

## `records` (alias `r`) — single-record operations

### `sg aws dns records get FQDN`

Show one record.

```bash
sg aws dns records get api.sg-compute.sgraph.ai
sg aws dns r get api.sg-compute.sgraph.ai --type AAAA --json
```

**Flags:** `--zone/-z Z`, `--type/-t T` (default `A`), `--json`

### `sg aws dns records add [INSTANCE|FQDN] [FQDN]`  ⚠ mutates

Create an A record. Three forms:

```bash
# 1. Latest running instance + derived name
SG_AWS__DNS__ALLOW_MUTATIONS=1 sg aws dns records add --yes --wait

# 2. Latest instance, explicit FQDN
SG_AWS__DNS__ALLOW_MUTATIONS=1 sg aws dns records add api.sg-compute.sgraph.ai --yes

# 3. Specific instance + explicit FQDN
SG_AWS__DNS__ALLOW_MUTATIONS=1 sg aws dns records add i-0abc123 api.sg-compute.sgraph.ai --yes

# 4. Explicit IP (no instance lookup)
SG_AWS__DNS__ALLOW_MUTATIONS=1 sg aws dns records add api.sg-compute.sgraph.ai \
  --value 10.0.0.1 --yes
```

**Flags:** `--value/-v IP`, `--type/-t T` (default `A`), `--ttl N` (default 60),
`--zone/-z Z`, `--yes`, `--no-verify`, `--wait`, `--wait-timeout N`,
`--force` (skip pre-existence check), `--json`.

### `sg aws dns records update NAME`  ⚠ mutates

Upsert. `--value` is required.

```bash
SG_AWS__DNS__ALLOW_MUTATIONS=1 \
  sg aws dns records update api.sg-compute.sgraph.ai --value 10.0.0.2 --yes
```

### `sg aws dns records delete NAME`  ⚠ mutates

```bash
SG_AWS__DNS__ALLOW_MUTATIONS=1 \
  sg aws dns records delete tmp.sg-compute.sgraph.ai --yes
```

**Flags:** `--type/-t T`, `--zone/-z Z`, `--yes`, `--json`.

### `sg aws dns records check NAME`

Propagation / consistency check. **Authoritative-only by default** (queries the 4 R53 NS for the zone directly — no public-resolver cache pollution).

```bash
sg aws dns records check api.sg-compute.sgraph.ai
sg aws dns records check api.sg-compute.sgraph.ai --expect 10.0.0.1
```

Opt into cache-polluting modes when you specifically want them:

```bash
# 8 public resolvers — pollutes caches at Google, Cloudflare, Quad9 …
sg aws dns records check api.sgraph.ai --public-resolvers --yes

# Local resolver — pollutes your laptop/EC2 stub resolver cache
sg aws dns records check api.sgraph.ai --local --yes

# All three layers
sg aws dns records check api.sgraph.ai --all --yes
```

**Flags:** `--type/-t T`, `--zone/-z Z`, `--expect VALUE`,
`--public-resolvers` (cache-polluting), `--local` (cache-polluting), `--all` (cache-polluting),
`--yes` (skip the cache-pollution warning), `--min-resolvers N` (quorum for `--public-resolvers`, default 5/8), `--json`.

---

## `instance` (alias `i`) — DNS ↔ EC2

### `sg aws dns instance create-record [instance-id|name-tag]`  ⚠ mutates

Create an A record pointing at an EC2 instance's public IP. Omit the argument → uses the latest running instance.

```bash
SG_AWS__DNS__ALLOW_MUTATIONS=1 \
  sg aws dns instance create-record --name api.sg-compute.sgraph.ai --yes --wait
```

**Flags:** `--name FQDN`, `--zone/-z Z`, `--ttl N` (default 60),
`--type/-t T` (default `A`), `--yes`, `--no-verify`, `--force`,
`--wait`, `--wait-timeout N`, `--json`.

---

## What backs this

Code lives in `sgraph_ai_service_playwright__cli/aws/dns/`:

| Class | What it does |
|-------|-------------|
| `Route53__AWS__Client` | Wraps boto3 — list zones, CRUD records, wait for change INSYNC |
| `Route53__Zone__Resolver` | Resolve FQDN → owning hosted zone |
| `Route53__Instance__Linker` | Look up EC2 instance by ID/name tag → public IP |
| `Route53__Check__Orchestrator` | Coordinate multi-resolver propagation checks |
| `Route53__Authoritative__Checker` | Query the 4 R53 NS directly (cache-safe) |
| `Route53__Public_Resolver__Checker` | Query 8 public DNS resolvers (cache-polluting) |
| `Route53__Local__Checker` | Query host default resolver via `dig` (cache-polluting) |
| `Route53__Smart_Verify` | Post-mutation verification orchestrator |
| `Dig__Runner` | `dig` subprocess wrapper |

Tests: `tests/unit/sgraph_ai_service_playwright__cli/aws/dns/`.
