---
title: "04 — Safety & cleanup — the resource ledger and three-layer guarantee"
file: 04__safety-and-cleanup.md
author: Architect (Claude)
date: 2026-05-16 (UTC hour 15)
parent: README.md
---

# 04 — Safety & cleanup

The most important section of this brief. Everything else is dead-on-arrival if the harness leaks.

> **Hard guarantee:** after any harness run — successful, failed, Ctrl-C'd, OOM-killed, or interrupted by AWS rate-limiting — the AWS account is in the same state as it was before the run. No orphan distributions, no orphan Lambdas, no orphan A records, no orphan certs.

That guarantee is delivered by **three independent mechanisms** plus a **session-level sweeper**. Any one mechanism failing should not leak.

---

## 1. The resource ledger

Every mutation gets paired with a registration.

### 1.1 Schema

```python
class Schema__Lab__Ledger__Entry(Type_Safe):
    run_id           : Safe_Str__Lab__Run_Id              # e.g. "2026-05-16T14-30-00Z__a7b2c3"
    entry_id         : Safe_Str__Lab__Entry_Id            # uuid4
    created_at       : Safe_Str__Timestamp                # ISO 8601 UTC
    expires_at       : Safe_Str__Timestamp                # created_at + lab_resource_max_ttl (default 1 h)
    resource_type    : Enum__Lab__Resource_Type           # R53_RECORD | CF_DISTRIBUTION | LAMBDA | LAMBDA_URL | ACM_CERT | EC2_INSTANCE | SG | IAM_ROLE | SSM_PARAM
    resource_id      : Safe_Str__Lab__Resource_Id         # e.g. "/hostedzone/Z01.../record-set/lab-prop-...A"
    cleanup_payload  : Dict__Str__Str                     # everything the teardown needs (zone_id, name, type, value, …)
    teardown_order   : int                                # smaller runs first on cleanup; CF (10) before Lambda (20) before A record (30)
    state            : Enum__Lab__Entry__State            # PENDING | DELETED | FAILED | ABANDONED
```

### 1.2 Storage

One file per run: `.sg-lab/ledger/<run-id>.jsonl`. Append-only. Each line is one entry. The ledger file is the source of truth, not memory.

```
.sg-lab/
├── ledger/
│   ├── 2026-05-16T14-30-00Z__a7b2c3.jsonl
│   └── 2026-05-16T14-45-00Z__b8c4d2.jsonl
├── runs/
│   ├── 2026-05-16T14-30-00Z__a7b2c3/
│   │   ├── result.json
│   │   ├── timeline.txt
│   │   └── stdout.log
│   └── …
└── state.json                                  # last_run_id, last_sweep_at, etc.
```

### 1.3 The pairing pattern

Every create+register goes through a single helper:

```python
def create_and_register(self, resource_type, factory, cleanup_payload, teardown_order, ttl_seconds=3600):
    entry = Schema__Lab__Ledger__Entry(
        run_id          = self.run_id                                                         ,
        entry_id        = uuid4().hex                                                         ,
        created_at      = utc_now_iso()                                                       ,
        expires_at      = utc_now_iso(add_seconds=ttl_seconds)                                ,
        resource_type   = resource_type                                                       ,
        resource_id     = ''                                                                  ,
        cleanup_payload = cleanup_payload                                                     ,
        teardown_order  = teardown_order                                                      ,
        state           = Enum__Lab__Entry__State.PENDING                                     ,
    )
    self.ledger.append(entry)                                                                 # WRITE TO DISK FIRST
    try:
        resource_id = factory()                                                               # the actual AWS call
    except Exception:
        entry.state = Enum__Lab__Entry__State.FAILED
        self.ledger.update(entry)
        raise
    entry.resource_id = resource_id
    self.ledger.update(entry)
    return resource_id
```

**Critical:** the entry is written **before** the factory is called. If the AWS call partially succeeds (e.g. the API returns OK but the network drops the response), the ledger still records the attempt and the sweeper can find the resource by tag.

### 1.4 Tagging convention

Every taggable resource gets a fixed set of AWS tags:

| Tag key | Value | Why |
|---------|-------|-----|
| `sg:lab` | `1` | Discoverable filter |
| `sg:lab:run-id` | `<run-id>` | Trace back to ledger |
| `sg:lab:experiment` | `<experiment-name>` | What we were measuring |
| `sg:lab:expires-at` | `<iso8601>` | Sweeper's primary key |
| `sg:lab:created-by` | `<aws-caller-identity>` | Audit |

These tags are **the safety net** — even if the ledger is corrupt, the sweeper can find every lab resource.

---

## 2. The three teardown mechanisms

### 2.1 Layer 1 — synchronous teardown (the happy path)

Every experiment is wrapped:

```python
def run_experiment(self, experiment):
    self.ledger.open(self.run_id)
    try:
        result = experiment.execute()
    finally:
        self._teardown_synchronous()
    return result

def _teardown_synchronous(self):
    entries = self.ledger.entries_sorted_by_teardown_order()
    for entry in entries:
        if entry.state != Enum__Lab__Entry__State.PENDING:
            continue
        try:
            self._teardown_one(entry)                                                         # dispatches by resource_type
            entry.state = Enum__Lab__Entry__State.DELETED
        except Exception as exc:
            entry.state = Enum__Lab__Entry__State.FAILED
            self.ledger.record_teardown_error(entry, exc)
            continue                                                                          # keep going on other resources
        finally:
            self.ledger.update(entry)
```

Every resource gets its own teardown — failures don't cascade. The ledger ends with FAILED entries that the sweeper handles.

### 2.2 Layer 2 — atexit + signal handlers

The experiment runner registers handlers:

```python
import atexit, signal

def install_safety_net(harness):
    def emergency_teardown(*args, **kwargs):
        if not harness.ledger.has_pending_entries():
            return
        harness.log('[SAFETY] Emergency teardown triggered.')
        harness._teardown_synchronous()
    atexit.register(emergency_teardown)
    signal.signal(signal.SIGINT,  emergency_teardown)                                         # Ctrl-C
    signal.signal(signal.SIGTERM, emergency_teardown)                                         # `kill`
    # SIGKILL cannot be trapped — Layer 3 covers that case
```

This covers crashes inside the experiment, Ctrl-C, and most `kill` paths. It does NOT cover SIGKILL, hard reboots, OOM kills.

### 2.3 Layer 3 — the leak sweeper

```
sg aws lab sweep [--apply] [--older-than 1h] [--run-id <id>]
```

Sweeps all AWS resources tagged `sg:lab=1` whose `sg:lab:expires-at` is in the past:

1. List candidate resources by tag:
   - Route 53: scan zones for records named `lab-*` (Route 53 doesn't support tags on records; we fall back to name pattern + reading the resource_id in the ledger).
   - CloudFront: `list_distributions` → filter by tag `sg:lab=1`.
   - Lambda: `list_functions` → for each, `list_tags` → filter.
   - ACM: `list_certificates` → for each, `list_tags_for_certificate` → filter.
   - EC2: `describe_instances` with tag filter — but only lab-tagged.
   - SSM Parameters: `describe_parameters` under `/sg-compute/lab/*` namespace.
   - IAM Roles: `list_roles` → filter by name prefix `sg-lab-`.
2. Print the candidate list as a table.
3. With `--apply`, delete in `teardown_order`.

The sweeper is the **session-level guarantee**. The advised workflow is:

```bash
sg aws lab sweep                                  # start every session — show me anything stale
sg aws lab sweep --apply                          # delete anything stale
sg aws lab run E11 propagation-timeline           # run an experiment
sg aws lab sweep                                  # at session end — verify clean
```

### 2.4 Layer 4 — the orphan-by-design TTL

Every lab resource carries `sg:lab:expires-at` in its **tags**. After that timestamp, the resource is considered abandoned regardless of ledger state. Default TTL is **1 hour**. The sweeper finds these and deletes them.

This means: even if all of Layers 1–3 fail (corrupt ledger, missing sweeper run, process gone), the worst case is `1 h × N concurrent runs` of orphan resources, which the *next* sweeper run finds. That's tolerable.

---

## 3. The teardown order

Resources MUST be torn down in dependency order. This is the canonical order, encoded in `Enum__Lab__Resource_Type.teardown_order`:

| Order | Resource | Why this order |
|------:|----------|----------------|
| 10 | CF distribution (disable then delete) | Slowest; must finish before deleting upstream Lambda or cert |
| 20 | Route 53 ALIAS to a CF distribution | Cannot delete CF before its alias is gone |
| 30 | Route 53 A records (non-alias) | Independent; delete next |
| 40 | Lambda Function URL | Must go before the Lambda function |
| 50 | Lambda function | Independent after URL gone |
| 60 | ACM cert (only if minted for this run; **never** delete a shared cert) | Only safe once nothing references it |
| 70 | EC2 instance (terminate; for lab stacks only — never terminate a vault-app instance not owned by the lab) | Independent |
| 80 | Security groups (lab-tagged only) | After the EC2 |
| 90 | SSM parameters | Last; cheap |
| 100 | IAM roles | Last; needs all attachments removed first |

CloudFront is the wrinkle: `delete_distribution` requires `Enabled=false` AND `Status=Deployed`, which takes ~15-20 min after disable. The teardown for CF is therefore **asynchronous**:

1. `update_distribution` with `Enabled=false`
2. mark the ledger entry as `state=DELETED_PENDING_CF_DISABLE`
3. record a follow-up task in the ledger (`sg-lab/pending-deletes.jsonl`)
4. **the next `sg aws lab sweep` call** finishes the deletion if the distribution is now `Disabled + Deployed`

This means after a Tier-2 experiment the user might see "1 distribution pending final delete — re-run sweep in 20 min" — that's expected. The CF is *disabled* immediately (zero billing) and finishes deletion later.

---

## 4. Resource budget per experiment

Each experiment declares a budget. If exceeded, the harness aborts and tears down.

```python
class Lab__Experiment(Type_Safe):
    name           : str
    tier           : Enum__Lab__Tier
    budget_seconds : int = 300                                                                # default 5 min wall-clock
    budget_resources : Dict__Str__Int                                                          # e.g. {'R53_RECORD': 50, 'LAMBDA': 1}
    ...
```

Going over the resource budget is a code bug — the harness aborts and ledger-teardowns everything. Going over the time budget is usually waiting for AWS — the harness logs a timeout, records the partial result, and tears down. Either way, no leak.

---

## 5. The "what could go wrong" checklist

Enumerated so each gets a mitigation.

| Failure mode | Mitigation |
|--------------|-----------|
| Experiment code throws | `try/finally` calls Layer 1 teardown |
| Ctrl-C mid-experiment | SIGINT handler in Layer 2 |
| `kill -9` of the process | Layer 3 sweeper finds via tags |
| Hard kernel reboot mid-experiment | Layer 4 expires-at + Layer 3 sweeper next run |
| AWS API call hangs forever | Per-call timeouts (boto3 config: `connect_timeout=10, read_timeout=30`); experiment also has a hard wall-clock budget |
| AWS API returns OK but network drops the response (so ledger doesn't know the resource_id) | Tagging carries the run-id; sweeper finds it by tag |
| Sweeper deletes someone *else's* resource that happens to have the same name pattern | Tags are checked **as well as** name patterns; both must match `sg:lab=1` + correct prefix |
| Sweeper runs against the wrong AWS account | Every harness call prints the AWS account id from STS::GetCallerIdentity and exits if it doesn't match `SG_AWS__LAB__EXPECTED_ACCOUNT_ID` env var (when set) |
| Two operators run experiments in the same account | Run-ids are unique per process; tags include the operator's caller identity; sweeper has a `--mine` flag that filters by caller |
| CF distribution stuck in `In Progress` when we try to delete | Pending-deletes queue; the next sweep handles it |
| A Route 53 record we created points at something we shouldn't have used (e.g. someone's production EC2 by accident) | All A-record VALUES are restricted to TEST-NET-1/2/3 (`192.0.2.0/24, 198.51.100.0/24, 203.0.113.0/24`) or to explicitly-lab-tagged resources. The harness refuses to write a non-test-net IP into a record without `--force-real-ip` |
| Lab provisions a Lambda that runs forever (recursion bug) and accrues huge cost | Hard `timeout=30` and `reserved_concurrency=2` on every lab Lambda |
| Operator runs `sg aws lab sweep --apply` against production-tagged resources | The sweeper *only* deletes resources where ALL of `sg:lab=1`, `sg:lab:run-id`, `sg:lab:expires-at` are present. Resources missing any of these tags are ignored even if they match a name pattern |

The last row is the most important — the sweeper is **defensive against itself**.

---

## 6. The `--dry-run` mode

Every mutating experiment supports `--dry-run`. Behaviour:

- Walks every step that would mutate AWS.
- Logs `[DRY-RUN] WOULD upsert_record(zone=..., name=..., value=..., ttl=...)`.
- Returns an empty result with a flag set.
- Never opens a real ledger entry.

This is the safest first-touch for any experiment. The CLI prints the dry-run output before asking for a confirmation (when running interactively) for Tier-2 experiments.

---

## 7. The "where do they go?" addresses

| Output | Path |
|--------|------|
| Ledger files | `.sg-lab/ledger/<run-id>.jsonl` |
| Run results | `.sg-lab/runs/<run-id>/result.json` |
| Run timelines | `.sg-lab/runs/<run-id>/timeline.txt` |
| Run stdout | `.sg-lab/runs/<run-id>/stdout.log` |
| Pending CF deletes | `.sg-lab/pending-deletes.jsonl` |
| Last-sweep state | `.sg-lab/state.json` |

All under `.sg-lab/` in the repo root, in `.gitignore`. The user (or CI) can blow the directory away at any time without affecting anything but local history.

---

## 8. The acceptance test for the safety story

Before any Tier-2 experiment is checked in, this test passes:

```
1. Run E27 (the biggest experiment, creates ~6 resources)
2. SIGKILL the process at a random point each iteration (run 10×)
3. After each kill: `sg aws lab sweep --apply --older-than 0s` runs
4. Assert: `aws cloudfront list-distributions --tag-key sg:lab` returns []
5. Assert: every lab-tagged resource across the account is gone
```

This is a deploy-via-pytest test under `tests/integration/sgraph_ai_service_playwright__cli/aws/lab/test_safety.py`, gated by `SG_AWS__LAB__ALLOW_MUTATIONS=1 SG_AWS__LAB__DESTROY_TEST=1`. Run before any release that touches the harness.
