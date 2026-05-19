---
title: "`sg vault-app fargate` — orchestrator + service design"
status: plan
audience: dinis_cruz
author: claude-opus-4-7
date: 2026-05-19
parent: ./00__overview.md
---

# `sg vault-app fargate` — orchestrator design

## File layout

```
sg_compute_specs/vault_app/fargate/
├── cli/
│   ├── Cli__Vault_App__Fargate.py           parent app, mounts sub-apps
│   ├── Cli__Vault_App__Fargate__Setup.py    setup check/status/create/update/delete/plan/show
│   ├── Cli__Vault_App__Fargate__Start.py    start/stop/restart/health/logs/url/open
│   ├── Cli__Vault_App__Fargate__Config.py   config show/set/unset
│   └── Cli__Vault_App__Fargate__Info.py     list/info/timings
├── service/
│   ├── Vault_App__Fargate__Spec.py          vault constants (image, ports, env contract)
│   ├── Vault_App__Fargate__Tags__Reader.py  cluster tags → Schema__VAF__Cluster__Config (Q3)
│   ├── Vault_App__Fargate__Tags__Writer.py  builds the VaultApp__* tag set during setup (Q3)
│   ├── Vault_App__Fargate__Setup.py         per-phase setup/check/teardown orchestrator
│   ├── Vault_App__Fargate__Starter.py       the fast-path orchestrator
│   ├── Vault_App__Fargate__Health.py        HTTP polling (extract from Cli__Vault_Publish wake pattern)
│   ├── Vault_App__Fargate__Timings__Store.py persist last N start timings to ~/.cache/sg/
│   ├── Vault_App__Fargate__Cluster__Resolver.py  --cluster | env | sole-tagged-cluster (Q4 revision)
│   ├── Vault_App__Fargate__Slug__Resolver.py     --slug | sole-running-task-in-cluster → task arn (Q4 revision)
│   ├── Vault_App__Fargate__Image__Mirror.py shells docker pull/tag/push for Q5
│   └── Mutation__Gate__Scope.py             env-var scope for the single ALLOW_MUTATIONS gate (Q2)
├── schemas/
│   ├── Schema__VAF__Cluster__Config.py      resolved-from-tags view (replaces ___Config per Q3)
│   ├── Schema__VAF__Setup__Report.py        per-phase setup report
│   ├── Schema__VAF__Start__Report.py        start command output envelope (JSON)
│   ├── Schema__VAF__Phase__Result.py        single-phase result (name, status, duration_ms, error?)
│   └── Schema__VAF__Timings__Record.py      persisted historical timing (~/.cache/sg/, NOT config)
├── collections/
│   ├── List__Schema__VAF__Phase__Result.py
│   └── List__Schema__VAF__Timings__Record.py
├── enums/
│   ├── Enum__VAF__Setup__Phase.py           ECR / IAM / LOGS / CLUSTER / IMAGE_MIRROR / TASK_DEF / DNS
│   ├── Enum__VAF__Start__Phase.py           RESOLVE_TASK_DEF / RUN_TASK / WAIT_RUNNING / RESOLVE_ENI / DNS_UPSERT / WAIT_HEALTH
│   ├── Enum__VAF__Phase__Status.py          PENDING / RUNNING / OK / SKIPPED / WARN / ERROR
│   └── Enum__VAF__Storage__Mode.py          MEMORY / DISK / S3
└── primitives/
    └── Safe_Str__VAF__Slug.py               regex ^[a-z0-9][a-z0-9-]{1,40}$
```

## Class responsibilities

### `Vault_App__Fargate__Spec` (constants — single source of truth)

```python
class Vault_App__Fargate__Spec(Type_Safe):
    image_repo_name : Safe_Str__ECR__Repo_Name = 'sg-send-vault'
    image_tag       : str                       = 'latest'
    container_name  : str                       = 'vault'
    health_path     : str                       = '/info/health'
    http_port       : int                       = 8080
    https_port      : int                       = 443
    acme_port       : int                       = 80
    default_cpu     : str                       = '512'
    default_memory  : str                       = '1024'
    default_log_group : str                     = '/ecs/vault-app'
    default_cluster   : str                     = 'vault-app'
    default_task_def_family : str               = 'vault-app'

    def env_for_run(self, access_token: str,
                    seed_vault_keys: str = '', with_tls: bool = True) -> dict:
        # returns the exact env-var map vault expects (mirrors Vault_App__Compose__Template)
        # SEND__STORAGE_MODE is hard-coded to 'memory' per Q1 update — peer
        # vaults handle any persistence concern. No flag, no parameter.
```

No methods that touch AWS. Pure config.

### `Vault_App__Fargate__Setup`

```python
class Vault_App__Fargate__Setup(Type_Safe):
    spec          : Vault_App__Fargate__Spec          = None
    tags_writer   : Vault_App__Fargate__Tags__Writer  = None      # Q3: tags replace persisted config
    tags_reader   : Vault_App__Fargate__Tags__Reader  = None      # used by `check` and `update`
    image_mirror  : Vault_App__Fargate__Image__Mirror = None      # Q5: ECR mirror phase

    # Dependency-injected clients — never imported boto3 directly
    ecr_client     : ECR__AWS__Client      = None
    iam_client     : IAM__AWS__Client      = None
    fargate_client : Fargate__AWS__Client  = None
    logs_client    : Logs__AWS__Client     = None        # P0 — needs the new sg aws logs sub-app
    ec2_client     : EC2__AWS__Client      = None

    progress_cb    : object = None                       # callable(phase, status, detail='') — see 04

    def check (self, phases: list[Enum__VAF__Setup__Phase]) -> Schema__VAF__Setup__Report: ...
    def create(self, phases: list[Enum__VAF__Setup__Phase]) -> Schema__VAF__Setup__Report: ...
    def update(self, phases: list[Enum__VAF__Setup__Phase]) -> Schema__VAF__Setup__Report: ...
    def delete(self, phases: list[Enum__VAF__Setup__Phase]) -> Schema__VAF__Setup__Report: ...
    def plan  (self, phases: list[Enum__VAF__Setup__Phase]) -> list[str]: ...     # dry-run, no calls

    def _phase_ecr     (self, op): ...    # op ∈ {check, create, update, delete}
    def _phase_iam     (self, op): ...
    def _phase_logs    (self, op): ...
    def _phase_cluster (self, op): ...
    def _phase_task_def(self, op): ...
```

Each `_phase_*` method:
1. Calls `progress_cb(phase, PENDING)` then `progress_cb(phase, RUNNING)`
2. Wraps the action in `Phase__Timer` (see [04](./04__timing-instrumentation.md))
3. Emits a `Schema__VAF__Phase__Result` (status, duration_ms, error?)
4. Calls `progress_cb(phase, result.status)` so the CLI's live table updates

**Idempotency**: every `create` is an upsert. `_phase_ecr.create` calls
`sg aws ecr repo-create` and treats `RepositoryAlreadyExistsException` as OK
(returns SKIPPED). Same for IAM roles, log groups, clusters. The state
transitions in the live progress table:
- already-exists → ✓ SKIPPED (yellow)
- created        → ✓ OK (green)
- failed         → ✗ ERROR (red)

### `Vault_App__Fargate__Starter` (the fast path)

```python
class Vault_App__Fargate__Starter(Type_Safe):
    spec        : Vault_App__Fargate__Spec         = None
    tags_reader : Vault_App__Fargate__Tags__Reader = None   # Q3: reads cluster tags at start time
    # Cluster config (subnets, SGs, role ARNs, log group, image URI, port mappings)
    # is resolved in-memory at start via:
    #   describe_cluster(cluster_name)    → cluster tags → Schema__VAF__Cluster__Config (network + roles)
    #   describe_task_definition(family)  → image / port mappings / log config
    # Both calls fire in parallel — ~50 ms combined, no disk I/O.

    fargate_client : Fargate__AWS__Client = None
    ec2_client     : EC2__AWS__Client     = None
    dns_client     : DNS__AWS__Client     = None      # only if --with-aws-dns

    progress_cb    : object = None

    def start(self, request: Schema__VAF__Start__Request) -> Schema__VAF__Start__Report:
        timer = Phase__Timer()
        with timer.phase(Enum__VAF__Start__Phase.RESOLVE_CONFIG):    # Q3: parallel describes
            cluster_cfg, task_def = self._parallel_resolve(request.cluster_name)
        with timer.phase(Enum__VAF__Start__Phase.RUN_TASK):          ...
        with timer.phase(Enum__VAF__Start__Phase.WAIT_RUNNING):      ...   # Q9: live state in detail
        with timer.phase(Enum__VAF__Start__Phase.RESOLVE_ENI):       ...
        if request.with_aws_dns and cluster_cfg.dns_zone:
            with timer.phase(Enum__VAF__Start__Phase.DNS_UPSERT):    ...
        with timer.phase(Enum__VAF__Start__Phase.WAIT_HEALTH):       ...   # Q9: attempt N/M in detail
        return Schema__VAF__Start__Report(
            slug=..., task_arn=..., public_ip=..., vault_url=...,
            phases=timer.results(),
            task_ready_ms = timer.cumulative_through(WAIT_RUNNING),
            vault_ready_ms = timer.cumulative_through(WAIT_HEALTH),
            total_ms = timer.total_ms(),
        )
```

**Hot-path budget invariants** — enforced by tests:
- Zero `describe_*` calls before `run_task` (config is on disk)
- One single `describe_tasks` call per poll cycle, polled every 1 s, capped
  at 30 s
- HTTP probe uses adaptive backoff (initial 500 ms, max 2 s, total cap 30 s)
- No file writes during start besides the timings record at the end

### `Vault_App__Fargate__Health` (extracted from `sg vp wake`)

The existing wake command's HTTP-probe loop
(`sg_compute_specs/vault_publish/cli/Cli__Vault_Publish.py:158–195`) is the
exact pattern we want. Extract it into a re-usable class so both `vp wake`
and `vault-app fargate start` can share it.

```python
class Vault_App__Fargate__Health(Type_Safe):
    timeout_seconds : int = 30
    initial_delay   : float = 0.5
    max_delay       : float = 2.0

    def wait_for(self, url: str, access_token: str = '') -> Schema__VAF__Health__Result:
        # returns (ok: bool, status_code: int, attempts: int, duration_ms: int, last_error: str)
```

### `Vault_App__Fargate__Cluster__Resolver` + `Vault_App__Fargate__Slug__Resolver`

Two resolvers, separated per Q4-revision (slug ≠ cluster). Both used by
every task-level command (`stop / health / logs / url / open / restart /
info`) in this order: cluster first, then slug within that cluster.

```python
class Vault_App__Fargate__Cluster__Resolver(Type_Safe):
    fargate_client : Fargate__AWS__Client = None
    env_var        : str = 'SG_VAULT_APP__FARGATE__CLUSTER'

    def resolve(self, cluster_flag: str = '') -> str:
        # 1. cluster_flag if set
        # 2. os.environ.get(self.env_var) if set
        # 3. list_clusters() filtered to tag Stack=sg-vault-app-fargate; if
        #    exactly one → use it
        # 4. raise typer.BadParameter listing candidates


class Vault_App__Fargate__Slug__Resolver(Type_Safe):
    fargate_client : Fargate__AWS__Client = None

    def resolve(self, cluster_name: str, slug: str = '') -> str:
        # 1. slug if set; verify a RUNNING task exists in cluster with
        #    tag VaultApp__Slug=<slug>; raise if not
        # 2. otherwise: list RUNNING tasks in cluster; if exactly one →
        #    return its VaultApp__Slug tag value
        # 3. otherwise: raise typer.BadParameter listing candidate slugs

    def to_task_arn(self, cluster_name: str, slug: str) -> str:
        # cheap helper used after resolve() — one list_tasks + filter

    def check_unique(self, cluster_name: str, slug: str) -> None:
        # used by `start` before run_task to fail fast on collision
        # raises ClusterSlugCollision if a RUNNING task already has the slug
```

Together these are the only AWS calls in the task-level commands' name
resolution: cluster + slug → task arn → action.

### `Vault_App__Fargate__Timings__Store`

```python
class Vault_App__Fargate__Timings__Store(Type_Safe):
    path : str = ''   # default: ~/.cache/sg/vault-app-fargate/timings.json

    def append(self, record: Schema__VAF__Timings__Record) -> None: ...
    def last  (self, n: int = 10) -> List__Schema__VAF__Timings__Record: ...
    def clear (self) -> None: ...
```

Backs the `sg vault-app fargate timings` command. Persists last N
`Schema__VAF__Start__Report` snapshots so users can see whether their cold
start is getting faster or slower over time.

## Wiring CLI ↔ service ↔ AWS client

Diagram for `start`:

```
sg vault-app fargate start --slug dinis-tue
  │
  ▼
Cli__Vault_App__Fargate__Start.start()
  │  - load config
  │  - build progress renderer (rich.live.Live + state dict)
  │  - hook progress_cb into Starter
  ▼
Vault_App__Fargate__Starter.start(request)
  │
  ├─ Fargate__AWS__Client.run_task(...)              # cluster + task-def + subnets + sgs from CONFIG
  ├─ Fargate__AWS__Client.describe_task(arn) × N     # poll every 1 s
  ├─ EC2__AWS__Client.describe_network_interfaces(...) # one call, resolve public IP
  ├─ DNS__AWS__Client.upsert_a(...)                  # optional
  └─ Vault_App__Fargate__Health.wait_for(url)        # HTTP poll
        │
        └─ Vault_App__Fargate__Timings__Store.append(record)
```

No code path inside `Starter` ever imports `boto3` or `botocore`. All AWS
calls go through the existing `aws/<service>/service/*__AWS__Client.py`
classes — that's how we satisfy the "all action through `sg aws *`" rule.

## Error handling

Mirror `sg vp setup` (`Cli__Setup.py:1026`):

- `botocore.exceptions.ClientError` → render the AWS error panel via
  `@spec_cli_errors` (already in use across the repo)
- `RuntimeError` from inside the orchestrator (e.g. "no public IP after 30 s")
  → friendly Rich panel + exit 1
- Anything else → re-raise (let pytest / dev tooling see it)

Setup phases report failures as `Schema__VAF__Phase__Result.status=ERROR`
and **stop the chain** unless `--continue-on-error` is passed. Setup `check`
never stops — it gathers all states and returns one combined report.

## Testing strategy

Same pattern as ECR / EC2 slices:

1. **No mocks, no patches.** Use in-memory clients
   (`Fargate__AWS__Client__In_Memory`, `ECR__AWS__Client__In_Memory`,
   `EC2__AWS__Client__In_Memory`, etc.) — we already have these from prior
   slices. Add `Logs__AWS__Client__In_Memory` for the new logs sub-app.
2. Inject in-memory clients into Setup / Starter via the factory constructors.
3. Test the full setup/start flow end-to-end against in-memory clients.
4. Time assertions are tested with a `Phase__Timer` stub that returns
   pre-baked durations — we test the *plumbing* (phases recorded, totals
   computed) not real wall-clock time.

A separate `tests/integration/` test (gated on a real AWS env var) drives
the actual end-to-end against a sandbox account — once per release, not on
every PR.

## Reading order

Continue to [`04__timing-instrumentation.md`](./04__timing-instrumentation.md)
for the `Phase__Timer` and live-progress design — that's the cross-cutting
piece that touches every class above.
