# 2026-04-25 — `sp el` (Ephemeral Kibana) — 2 / 3 — What we built

This is part two of a three-part debrief on the `sp elastic` slice.

| Part | File |
|------|------|
| 1 — Why we built this | `2026-04-25__sp-elastic-kibana__01-why.md` |
| 2 — **What we built** *(this doc)* | `2026-04-25__sp-elastic-kibana__02-what.md` |
| 3 — How to use it | `2026-04-25__sp-elastic-kibana__03-how-to-use.md` |

---

## CLI surface

`sp elastic` (alias `sp el`) is a Typer app with the following commands:

### Lifecycle

| Command | What it does |
|---|---|
| `sp el create [NAME]` | Launch a fresh ES + Kibana + nginx-TLS stack on m6i.xlarge. Bakes a 1h auto-terminate timer. Optional `--wait`, `--seed`. |
| `sp el create-from-ami [AMI-ID] [NAME]` | Fast launch from an "Ephemeral Kibana" AMI. Auto-picks the latest available AMI when no id given. |
| `sp el wait [NAME]` | Poll until Kibana returns 200 (~3 min cold, ~30-60s from AMI). Per-tick state / ES probe / Kibana probe. |
| `sp el list` | Table of stacks: name, instance, state, uptime, IP, Kibana URL. |
| `sp el info [NAME]` | Single-stack details including launch time and uptime. |
| `sp el delete [NAME] [--all] [-y]` | Terminate one stack or every stack in the region. |
| `sp el connect [NAME]` | SSM Session Manager interactive shell. |
| `sp el exec [NAME] -- COMMAND` | Run a shell command on the host via SSM. |
| `sp el health [NAME]` | 8-check diagnostic table. |
| `sp el harden [NAME]` | Hide Observability + Security + Fleet + ML side-nav groups. Idempotent. (Auto-runs at boot now; this is the manual fallback.) |

### Data lifecycle

| Command | What it does |
|---|---|
| `sp el seed [NAME]` | Generate 10k synthetic log docs, bulk-post to ES, create the Kibana data view, import the default 4-panel dashboard. Idempotent. Default ON: `--data-view`, `--dashboard`. |
| `sp el wipe [NAME] [-y]` | Delete the ES index + the Kibana data view + every saved object the dashboard import created (current + legacy IDs). Idempotent. |

### Saved objects

| Command | What it does |
|---|---|
| `sp el dashboard list / export / import` | Manage Kibana dashboards via `/api/saved_objects/*`. Export defaults to `includeReferencesDeep=true`. |
| `sp el data-view list / export / import` | Same three actions for Kibana data views (`type=index-pattern` under the hood). |

### AMI management

| Command | What it does |
|---|---|
| `sp el ami list` | List AMIs tagged `sg:purpose=elastic`. |
| `sp el ami create [STACK]` | **Default**: full chain from nothing — create + wait + seed + bake + delete source. Pass an existing stack name to bake it as-is. `--wait` blocks until available; `--keep-source` retains the source stack; `--password` overrides the bake-time password. |
| `sp el ami wait AMI-ID` | Poll until the AMI moves from pending → available. |
| `sp el ami delete AMI-ID [-y]` | Deregister + delete the underlying EBS snapshots (AWS keeps snapshots when you only deregister). |

## Architecture

### Topology on the EC2 instance

```
/opt/sg-elastic/
  docker-compose.yml      elasticsearch:8.13.4, kibana:8.13.4, nginx:alpine
  nginx.conf              TLS termination on :443, path-based routing
  certs/{tls.crt, tls.key}  self-signed at boot, SAN = public IP
  .env                    ELASTIC_PASSWORD, KIBANA_ENCRYPTION_KEY,
                          KIBANA_SERVICE_TOKEN (chmod 600)
  harden-kibana.sh        background script that PUTs disabledFeatures
```

### Port surface

| Port | Bound | Purpose |
|---|---|---|
| 443 | public | nginx TLS — `/` → Kibana, `/_elastic/*` → Elasticsearch |
| 5601 | 127.0.0.1 only | Kibana (not reachable from the SG) |
| 9200 | 127.0.0.1 only | Elasticsearch (not reachable from the SG) |

The nginx rewrite means we don't need a separate ingress rule for ES port 9200 — every request comes in on :443 and is routed by path.

### SG ingress

Single rule: caller's `/32` on port 443. Recorded in the SG's `sg:allowed-ip` tag at create time so `sp el health` can flag SG-vs-current-IP mismatches when the user's public IP rotates.

### IAM / SSM

Each stack carries an instance profile with `AmazonSSMManagedInstanceCore`. Powers `sp el connect`, `sp el exec`, and the SSM-side checks in `sp el health`.

## Boot sequence (cold path)

```
0s   ─── EC2 launches, cloud-init runs
~30s ─── Docker installed (dnf install)
~40s ─── Docker daemon up
~50s ─── docker compose pulls Elasticsearch image
~90s ─── elasticsearch container starts
~93s ─── ES /_cluster/health returns yellow ←── seed bulk-post can start here
~95s ─── service-account token minted
~100s── Kibana + nginx containers start
~115s── Kibana /api/status returns 200      ←── data view + dashboard import
~115s── harden script (background) PUTs disabledFeatures into default space
~158s── seed completes (data + dashboard)   [if --seed flag set]
```

## Boot sequence (AMI fast path)

```
0s   ─── EC2 launches from baked AMI
~5s  ─── cloud-init runs render_fast user-data (no install steps)
~15s ─── Docker daemon up; restart=unless-stopped containers come back
~80s ─── ES + Kibana ready (simultaneous tick because pre-warmed state)
```

## The 8 health checks

`sp el health` runs them in order:

| # | Check | Why |
|---|---|---|
| 1 | `ec2-state` | Instance must be running |
| 2 | `public-ip` | Instance must have a public IP |
| 3 | `sg-ingress` | Current caller IP must be in the SG's :443 allow list (most common cause of ConnectTimeout — your home/office IP rotated since `sp el create` baked it in) |
| 4 | `tcp-443` | `socket.create_connection` to public_ip:443 within 5s |
| 5 | `elastic` | `/_cluster/health` probe; yellow on single-node = WARN (normal), green = OK |
| 6 | `kibana` | `/api/status` probe |
| 7 | `ssm-boot-status` | `cat /var/log/sg-elastic-boot-status` via SSM |
| 8 | `ssm-docker` | `docker ps` via SSM (top 6 lines) |

Rollup logic: WARN doesn't fail the rollup (yellow on single-node is normal). Only FAIL flips it red.

## The default 4-panel dashboard

Generated programmatically by `Default__Dashboard__Generator` (legacy `visualization` saved-object type — Lens has too many migration hooks for hand-rolled JSON):

| Panel | Type | Aggregation |
|---|---|---|
| Log levels | donut | terms on `level.keyword` |
| Log volume over time | stacked vertical bar | date_histogram on `timestamp`, split by `level.keyword` |
| Top services | horizontal bar | terms on `service.keyword` |
| Average request duration over time | line | `avg(duration_ms)` over date_histogram |

Deterministic saved-object IDs (`sg-vis-*` + `sg-synthetic-overview`) so re-importing with `overwrite=true` is idempotent. Legacy `sg-lens-*` IDs from earlier attempts are also tracked so `sp el wipe` and `ensure_default_dashboard` clean them on every run — fixes the "Cannot read properties of undefined (reading 'layers')" crash that stale half-imported Lens objects caused.

## The harden script

Disables 25+ Kibana features in the default space's `disabledFeatures`, hiding the Observability / Security / Fleet / ML / Maps / Cases / Synthetics / SLO / Enterprise Search side-nav groups so the user only sees Discover / Dashboards / Visualize Library / Stack Management.

Two paths to apply:
- **Boot-time** (default): cloud-init writes `/opt/sg-elastic/harden-kibana.sh` and runs it via `nohup` after `docker compose up`. Polls Kibana until `/api/status` returns 200, then PUTs the merged space body. Persisted to `.kibana` index, so AMI snapshots are self-contained.
- **Runtime** (fallback): `sp el harden` calls the same Kibana Spaces API from the CLI host. For older AMIs that predate the boot-time integration, or for re-applying after a Kibana data wipe.

Single source of truth for the disabled-features list: `Kibana__Disabled_Features.DEFAULT_DISABLED_FEATURES` — both paths import from there.

## Module layout

```
sgraph_ai_service_playwright__cli/elastic/
  enums/
    Enum__Elastic__State                 PENDING / RUNNING / READY / TERMINATING / TERMINATED / UNKNOWN
    Enum__Elastic__Probe__Status         UNREACHABLE / AUTH_REQUIRED / RED / YELLOW / GREEN / UNKNOWN
    Enum__Kibana__Probe__Status          UNREACHABLE / UPSTREAM_DOWN / BOOTING / READY / UNKNOWN
    Enum__Health__Status                 OK / WARN / FAIL / SKIP
    Enum__Saved_Object__Type             DASHBOARD / DATA_VIEW
    Enum__Log__Level                     INFO / DEBUG / WARN / ERROR (synthetic data)
  primitives/
    Safe_Str__Elastic__Stack__Name       elastic-{adjective}-{scientist}
    Safe_Str__Elastic__Password
    Safe_Str__Diagnostic                 permissive ASCII+Latin-1 for error messages
    Safe_Str__IP__Address
    Safe_Str__Shell__Output
  schemas/
    Schema__Elastic__Create__Request     stack_name, region, instance_type, from_ami, caller_ip, max_hours, elastic_password
    Schema__Elastic__Create__Response    + AWS-side ids + Kibana URL
    Schema__Elastic__Info                public view (no password)
    Schema__Elastic__List                stacks list + region
    Schema__Elastic__Delete__Response
    Schema__Elastic__Seed__Request       + create_data_view + time_field_name + create_dashboard
    Schema__Elastic__Seed__Response      + last_http_status + data_view_* + dashboard_*
    Schema__Elastic__Health__Check       name + status + detail
    Schema__Elastic__Health__Response    stack_name + all_ok + checks
    Schema__Elastic__AMI__Info           ami_id + name + state + source_stack + creation_date
    Schema__Wait__Tick                   per-tick info for the wait loop
    Schema__Exec__Result                 stdout/stderr/exit_code/status/duration
    Schema__Log__Document                synthetic log row
    Schema__Kibana__Saved_Object         find()/list() row
    Schema__Kibana__Find__Response
    Schema__Kibana__Import__Result
    Schema__Kibana__Export__Result
    Schema__Kibana__Data_View__Result
    Schema__Kibana__Dashboard__Result
  collections/
    List__Schema__Elastic__Info
    List__Schema__Elastic__AMI__Info
    List__Schema__Elastic__Health__Check
    List__Schema__Kibana__Saved_Object
    List__Schema__Log__Document
  service/
    Elastic__Service                     pure-logic orchestrator (no boto3, no HTTP, no Typer)
    Elastic__AWS__Client                 boto3 boundary (EC2 + IAM + SSM)
    Elastic__HTTP__Client                base requests wrapper (kibana_probe + elastic_probe + bulk_post + delete_index)
    Kibana__Saved_Objects__Client        find / export / import / ensure_data_view / ensure_default_dashboard / disable_space_features
    Default__Dashboard__Generator        builds the dashboard ndjson programmatically
    Kibana__Disabled_Features            single source of truth for the harden feature list
    Elastic__User__Data__Builder         renders cloud-init for both full-install and fast-launch paths
    Caller__IP__Detector                 GET checkip.amazonaws.com
    Synthetic__Data__Generator           seedable random log generator
    AWS__Error__Translator               friendly hints for common boto3 errors
```

## Test coverage

- **165 unit tests** across the elastic suite (was 86 at slice start).
- **Zero mocks**: every collaborator is a real subclass-and-override (`Elastic__AWS__Client__In_Memory`, `Elastic__HTTP__Client__In_Memory`, `Kibana__Saved_Objects__Client__In_Memory`, `Caller__IP__Detector__In_Memory`).
- Test files mirror the service shape — one `test_*.py` per service method or schema area.
- Network-touching code (HTTP, AWS) is tested by overriding the seam (`request()` for HTTP, `ec2_client()` / `ssm_client()` for boto3) and returning canned `requests.Response` objects.
- The user-data builder tests assert against the rendered cloud-init string (no fixtures, no diff-snapshot).

## Notable bugs found and fixed during the slice

1. **Type_Safe `.json()` returned dict, not string** — bulk-post NDJSON body had dicts joined with `\n` causing `TypeError`. Fix: `json.dumps(doc.json())`.
2. **Rich markup escape** — ES error bodies contain `[/_bulk]` which Rich parsed as a closing markup tag, crashing twice (the user's seed table and then the error handler trying to render the MarkupError). Fix: `rich_escape()` everywhere user-controlled content gets interpolated.
3. **SSM ResponseCode falsy-zero** — `int(inv.get('ResponseCode', -1) or -1)` collapsed success (0) to -1 because 0 is falsy. Fix: explicit None check.
4. **Em-dash in Safe_Str__Diagnostic** — U+2014 isn't in the regex range `\xA1-\xFF`. Fix: replaced em-dashes with hyphens in detail strings.
5. **Lens dashboard HTTP 500** — hand-rolled Lens saved objects failed Kibana's migration. Fix: switched to legacy `visualization` saved-object type. Plus self-healing pre-clean of stale Lens documents that otherwise poison every subsequent saved-objects operation.
6. **`sp el exec` shlex.join wrapping** — single pre-composed shell command got re-quoted by `shlex.join`, breaking on the remote shell. Fix: `len(parts) == 1` special-case.

## Commit list

| SHA | Summary |
|---|---|
| `501f12b` | Surface seed HTTP errors + SG_ELASTIC_PASSWORD pre-flight |
| `72dd4a0` | Dashboard / data-view CLI + early ES-ready probe |
| `043ca9f` | Slim Kibana feature set in user-data (XPACK_*_ENABLED env vars) |
| `ccb5464` | Escape user-supplied text before Rich markup parser |
| `0c665d3` | `--max-hours` auto-terminate + uptime in list/info |
| `1e80d04` | `sp el health` — direct + SSM diagnostics |
| `1a1bbcd` | Fix SSM exit-code parsing collapsed success (0) to -1 |
| `aa2b4bd` | Seed auto-creates the Kibana data view |
| `446680b` | `sp el wipe` + health rollup ⚠ for warn-only |
| `6b82bdb` | `sp el create --wait --seed` one-shot bootstrap |
| `dbbaeb0` | Bootstrap timeline at end of create --wait --seed |
| `168c179` | Rewrite default dashboard using legacy visualization |
| `ac5ad88` | Clean stale Lens objects before/during dashboard import |
| `68fbe78` | Default dashboard in seed + `sp el harden` side-nav |
| `3223314` | Bake Kibana harden into EC2 boot (AMI-ready) |
| `48cd313` | `sp el delete --all` |
| `9e076e3` | `sp el ami {list,create,delete}` sub-commands |
| `ae8ab1f` | `sp el create-from-ami` fast launch (no install in cloud-init) |
| `56b8d96` | Consistent `--password` override + "Ephemeral Kibana" AMI label |
| `008dae1` | `sp el ami wait` + `--wait` flag on ami create |
| `0cd9059` | `sp el ami create --from-scratch` |
| `aa81f0a` | Make from-scratch the default for `sp el ami create` |
| `d9346b6` | `sp el create-from-ami` auto-picks the latest available AMI |

## Good failures vs bad failures

Following the project's debrief convention.

### Good failures (surfaced early, caught by tests, informed a better design)

- **Lens HTTP 500** — caught immediately by user testing. Drove the switch to legacy `visualization` and added the self-healing pre-clean in `ensure_default_dashboard`.
- **Em-dash regex rejection** — caught by health-check test the moment we added a feature. Pinned the limitation of `Safe_Str__Diagnostic`.
- **SSM exit-code falsy-zero** — caught by the user noticing "exit=-1 status=Success" in `sp el health` output. Drove a regression test that pins the ResponseCode parsing.
- **Rich markup crash** — caught by a real seed run. Drove a regression test that feeds the literal `[/_bulk]` pattern through the decorator.
- **shlex.join over-quoting in exec** — caught by user trying the printed copy-paste command. Drove `join_command_args_for_shell` extraction + unit test.

### Bad failures (silenced, worked around, or re-introduced — i.e. follow-up requests)

- **Boot-time harden didn't apply on at least one stack** — user's pic2 showed the default nav after a fresh launch. Diagnosis pending — needs the `/var/log/sg-elastic-harden.log` from that stack.
- **OpenSearch swap** — left as an unstarted follow-up. Not a failure per se but an open trade-off (Elastic license).

See part 3 ("How to use it") for the user-facing recipes.
