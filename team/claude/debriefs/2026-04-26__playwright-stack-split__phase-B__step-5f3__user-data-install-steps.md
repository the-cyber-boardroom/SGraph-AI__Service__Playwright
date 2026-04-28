# Phase B · Step 5f.3 — Expand user-data with Docker install + compose-up

**Date:** 2026-04-26.
**Commit:** `06bf140`.
**Plan:** `team/comms/plans/v0.1.96__playwright-stack-split/04__sp-os__opensearch.md`.
**Predecessor:** Step 5f.2 (compose template).

---

## What shipped

`USER_DATA_TEMPLATE` grew from a placeholder scaffold into a working AL2023 boot script:

1. Installs Docker via `dnf install -y docker` (AL2023 native; not yum/apt)
2. Installs the docker compose plugin into `/usr/local/lib/docker/cli-plugins/`
3. Writes the rendered compose YAML to `/opt/sg-opensearch/docker-compose.yml` via `cat > ... <<'SG_OS_COMPOSE_EOF'` heredoc
4. Bumps `vm.max_map_count` to 262144 — both runtime sysctl AND persistent `/etc/sysctl.d/99-sg-opensearch.conf` (OpenSearch 2.x refuses to start otherwise)
5. Runs `docker compose up -d` from the compose dir

Module-level constants (locked by test):
- `COMPOSE_DIR = '/opt/sg-opensearch'`
- `COMPOSE_FILE = '/opt/sg-opensearch/docker-compose.yml'`
- `LOG_FILE = '/var/log/sg-opensearch-boot.log'`

`render()` signature changed:
- **Before:** `render(stack_name, admin_password, region)`
- **After:** `render(stack_name, region, compose_yaml)` — `admin_password` removed; secret lives only inside `compose_yaml` (rendered upstream by `OpenSearch__Compose__Template`).

`PLACEHOLDERS` expanded to `(stack_name, region, log_file, compose_dir, compose_file, compose_yaml)`.

## Secret hygiene

The defensive test `test_render__does_not_carry_admin_password` asserts neither `ADMIN_PASSWORD` nor `admin_password` appears in the rendered user-data. The secret only flows through the compose YAML, which has its own embedding path. One place to leak.

## Tests

13 tests (was 6 in 5f.1):
- Shape: shebang, `set -euo`, canonical log path
- Substitutions: stack/region values; compose YAML embedded in heredoc; no leftover `{key}`
- Install steps: dnf Docker install, compose plugin path, `vm.max_map_count` (runtime + persistent), compose-up runs in compose dir
- Secret hygiene: no admin_password leakage
- Contract: `PLACEHOLDERS` matches; canonical paths under `/opt/sg-opensearch/`

## Files changed

```
M  sgraph_ai_service_playwright__cli/opensearch/service/OpenSearch__User_Data__Builder.py
M  tests/unit/sgraph_ai_service_playwright__cli/opensearch/service/test_OpenSearch__User_Data__Builder.py
```
