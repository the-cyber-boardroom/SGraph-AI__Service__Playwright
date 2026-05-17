---
title: "05 — Module layout"
file: 05__module-layout.md
author: Architect (Claude)
date: 2026-05-16 (UTC hour 15)
parent: README.md
---

# 05 — Module layout

Folder structure, class layout, schema list, CLI surface. Mirrors `sg aws dns` exactly.

---

## 1. Folder

```
sgraph_ai_service_playwright__cli/aws/lab/
├── __init__.py
├── cli/
│   ├── __init__.py
│   └── Cli__Lab.py                                                                           # `sg aws lab …` Typer surface
├── service/
│   ├── __init__.py
│   ├── Lab__Runner.py                                                                        # The harness — opens ledger, runs experiment, tears down
│   ├── Lab__Ledger.py                                                                        # Append-only JSONL ledger with file locking
│   ├── Lab__Sweeper.py                                                                       # The leak sweeper (tag-driven)
│   ├── Lab__Tagger.py                                                                        # Centralised tag application — one place to set sg:lab tags
│   ├── Lab__Safety__Account_Guard.py                                                         # Refuses to run against the wrong AWS account
│   ├── Lab__Timing.py                                                                        # high-precision timing primitive (perf_counter, ISO-iso, durations)
│   ├── teardown/
│   │   ├── __init__.py
│   │   ├── Lab__Teardown__Dispatcher.py                                                      # Maps Enum__Lab__Resource_Type → teardown fn
│   │   ├── Lab__Teardown__R53.py                                                             # delete_record-set with idempotency
│   │   ├── Lab__Teardown__CF.py                                                              # disable-then-delete; pending-deletes queue
│   │   ├── Lab__Teardown__Lambda.py                                                          # delete url + function
│   │   ├── Lab__Teardown__ACM.py                                                             # delete cert (lab-minted only)
│   │   ├── Lab__Teardown__EC2.py                                                             # terminate instance + SG
│   │   ├── Lab__Teardown__SSM.py                                                             # delete parameters
│   │   └── Lab__Teardown__IAM.py                                                             # detach + delete role
│   ├── experiments/
│   │   ├── __init__.py
│   │   ├── Lab__Experiment.py                                                                # abstract base — defines budget, tier, name
│   │   ├── dns/
│   │   │   ├── E01__zone_inventory.py
│   │   │   ├── E02__resolver_latency.py
│   │   │   ├── E03__authoritative_ns_latency.py
│   │   │   ├── E04__wildcard_pre_check.py
│   │   │   ├── E10__insync_distribution.py
│   │   │   ├── E11__propagation_timeline.py
│   │   │   ├── E12__wildcard_vs_specific.py
│   │   │   ├── E13__ttl_respect.py
│   │   │   └── E14__delete_propagation.py
│   │   ├── cf/
│   │   │   ├── E20__cf_distribution_inspect.py
│   │   │   ├── E21__cf_edge_locality.py
│   │   │   ├── E22__cf_tls_handshake.py
│   │   │   ├── E25__cf_cache_policy_enforcement.py
│   │   │   ├── E26__cf_origin_error_handling.py
│   │   │   └── E27__full_cold_path_end_to_end.py
│   │   ├── lambda_/
│   │   │   ├── E30__lambda_cold_start.py
│   │   │   ├── E31__lambda_deps_impact.py
│   │   │   ├── E32__lambda_stream_vs_buffer.py
│   │   │   ├── E33__lambda_internal_r53_call.py
│   │   │   ├── E34__lambda_internal_ec2_curl.py
│   │   │   └── E35__lambda_function_url_vs_direct.py
│   │   └── transition/
│   │       ├── E40__dns_swap_window.py
│   │       ├── E41__stop_race_window.py
│   │       └── E42__concurrent_cold_thunder.py
│   ├── renderers/
│   │   ├── __init__.py
│   │   ├── Render__Table.py                                                                  # Rich tables
│   │   ├── Render__Timeline__ASCII.py                                                        # one-pixel-per-100ms ASCII plot
│   │   ├── Render__Histogram__ASCII.py                                                       # for latency distributions
│   │   └── Render__JSON.py                                                                   # pretty JSON dumps
│   ├── temp_clients/                                                                          # narrow boto3 wrappers we'll DELETE once sg aws cf / lambda land
│   │   ├── __init__.py
│   │   ├── Lab__CloudFront__Client__Temp.py
│   │   └── Lab__Lambda__Client__Temp.py
│   └── lambdas/                                                                              # tiny in-tree Lambda functions deployed by experiments
│       ├── __init__.py
│       ├── lab_waker_stub/
│       │   ├── handler.py                                                                    # FastAPI + LWA; returns warming HTML or echo
│       │   └── requirements.txt
│       ├── lab_error_origin/
│       │   ├── handler.py                                                                    # returns 503, 502, timeouts, etc per query param
│       │   └── requirements.txt
│       └── lab_internal_caller/
│           ├── handler.py                                                                    # times internal AWS calls (E33, E34)
│           └── requirements.txt
├── schemas/
│   ├── __init__.py
│   ├── Schema__Lab__Ledger__Entry.py
│   ├── Schema__Lab__Run__Result.py
│   ├── Schema__Lab__Experiment__Metadata.py
│   ├── Schema__Lab__Timing__Sample.py
│   ├── Schema__Lab__Resolver__Observation.py
│   ├── Schema__Lab__Sweep__Report.py
│   ├── Schema__Lab__Account__Identity.py
│   ├── Schema__Lab__Result__DNS__Propagation.py
│   ├── Schema__Lab__Result__DNS__Wildcard_Vs_Specific.py
│   ├── Schema__Lab__Result__CF__Origin_Error.py
│   ├── Schema__Lab__Result__Lambda__Cold_Start.py
│   ├── Schema__Lab__Result__Transition__DNS_Swap.py
│   └── … (one Schema__Lab__Result__* per experiment)
├── enums/
│   ├── __init__.py
│   ├── Enum__Lab__Resource_Type.py                                                           # R53_RECORD | CF_DISTRIBUTION | LAMBDA | ACM_CERT | EC2_INSTANCE | SG | IAM_ROLE | SSM_PARAM
│   ├── Enum__Lab__Entry__State.py                                                            # PENDING | DELETED | FAILED | ABANDONED | DELETED_PENDING_CF_DISABLE
│   ├── Enum__Lab__Tier.py                                                                    # READ_ONLY | MUTATING_LOW | MUTATING_HIGH
│   ├── Enum__Lab__Tag__Key.py                                                                # SG_LAB | SG_LAB_RUN_ID | SG_LAB_EXPERIMENT | SG_LAB_EXPIRES_AT | SG_LAB_CREATED_BY
│   └── Enum__Lab__Experiment__Status.py                                                      # PENDING | RUNNING | OK | FAILED | TIMEOUT | ABORTED
├── primitives/
│   ├── __init__.py
│   ├── Safe_Str__Lab__Run_Id.py                                                              # ISO-ts-z__<6-char nonce>
│   ├── Safe_Str__Lab__Entry_Id.py                                                            # uuid4 hex
│   ├── Safe_Str__Lab__Resource_Id.py                                                         # opaque AWS-side id
│   ├── Safe_Str__Lab__Experiment_Name.py                                                     # e.g. "propagation-timeline"
│   ├── Safe_Str__Timestamp.py                                                                # ISO 8601 UTC
│   └── Safe_Int__Duration_Ms.py
└── collections/
    ├── __init__.py
    ├── List__Schema__Lab__Ledger__Entry.py
    ├── List__Schema__Lab__Timing__Sample.py
    └── List__Schema__Lab__Resolver__Observation.py
```

About **40 production files** + 30 test files. Most of the production files are small (each experiment file is ~100–200 lines of pure orchestration).

---

## 2. The base `Lab__Experiment` class

```python
class Lab__Experiment(Type_Safe):
    """Abstract base every experiment extends."""
    name             : Safe_Str__Lab__Experiment_Name
    tier             : Enum__Lab__Tier
    budget_seconds   : int = 300
    budget_resources : Dict__Str__Int                                                          # e.g. {'R53_RECORD': 50}

    def execute(self, runner: 'Lab__Runner') -> Schema__Lab__Run__Result:
        raise NotImplementedError

    def metadata(self) -> Schema__Lab__Experiment__Metadata:
        return Schema__Lab__Experiment__Metadata(
            name             = self.name           ,
            tier             = self.tier           ,
            budget_seconds   = self.budget_seconds ,
            budget_resources = self.budget_resources,
            description      = self.__doc__ or ''  ,
        )
```

Each experiment is a single class with one method (`execute`). The runner instantiates it, calls `execute(runner)`, the experiment uses `runner` for `create_and_register`, `dig`, `time`, `log`. No experiment talks to boto3 directly; everything goes through the runner or the existing clients (`Route53__AWS__Client`, etc.).

---

## 3. The `Lab__Runner` API surface

This is the class every experiment touches. Small and intentional.

```python
class Lab__Runner(Type_Safe):
    run_id             : Safe_Str__Lab__Run_Id
    ledger             : Lab__Ledger
    tagger             : Lab__Tagger
    account_guard      : Lab__Safety__Account_Guard
    timing             : Lab__Timing
    teardown_dispatcher: Lab__Teardown__Dispatcher

    # ── lifecycle ────────────────────────────────────────────────────────────
    def start(self, experiment: Lab__Experiment) -> None: ...                                 # account_guard + ledger.open + signal handlers
    def teardown(self) -> List__Schema__Lab__Ledger__Entry: ...                               # iterate ledger, run teardown_dispatcher per entry
    def abort(self, reason: str) -> None: ...

    # ── resource management ──────────────────────────────────────────────────
    def create_and_register(self, *, resource_type, factory, cleanup_payload,
                             teardown_order, ttl_seconds=3600) -> str: ...

    # ── timing helpers ───────────────────────────────────────────────────────
    def now_iso(self) -> str: ...
    def stopwatch(self, label: str) -> 'ContextManager[Lab__Timing__Sample]': ...

    # ── logging ──────────────────────────────────────────────────────────────
    def log(self, msg: str, *, level='info', extra: dict = None) -> None: ...

    # ── client accessors (reuse existing classes) ────────────────────────────
    def r53(self) -> Route53__AWS__Client: ...
    def cf(self) -> 'CloudFront__AWS__Client | Lab__CloudFront__Client__Temp': ...            # use real once it exists
    def lambda_(self) -> 'Lambda__AWS__Client | Lab__Lambda__Client__Temp': ...
    def dig(self) -> Dig__Runner: ...
    def authoritative_checker(self) -> Route53__Authoritative__Checker: ...
    def public_resolver_checker(self) -> Route53__Public_Resolver__Checker: ...
```

This is the **whole** surface an experiment author needs to know.

---

## 4. CLI surface

```
sg aws lab
├── list                                          — show every available experiment + tier + budget
├── show <experiment-id>                          — show metadata + last result snapshot
├── run <experiment-id> [opts...]                 — run one experiment
│   --dry-run                                     — print what would happen, no AWS calls
│   --json                                        — output JSON to stdout (suppress Rich)
│   --output-dir <path>                           — override .sg-lab/runs/...
│   --tier-2-confirm                              — required for Tier-2 (the CLI also prompts interactively)
├── runs
│   list [--last N] [--experiment <id>]           — list past run-ids
│   show <run-id>                                 — render a past result
│   diff <run-id-A> <run-id-B>                    — diff two runs of the same experiment (timings, observations)
├── sweep
│   [--apply] [--older-than 1h] [--run-id <id>]   — find and (optionally) delete leaked resources
│   --mine                                        — only resources tagged with my caller identity
│   --pending                                     — finish off CF distributions that are now Disabled+Deployed
├── account
│   show                                          — STS get-caller-identity + region
│   set-expected <account-id>                     — write SG_AWS__LAB__EXPECTED_ACCOUNT_ID to .sg-lab/state.json
├── ledger
│   show <run-id>                                 — render a past ledger
│   replay <run-id>                               — re-run teardown for a past ledger (recovery)
└── serve [--port 8090]                           — optional FastAPI viewer for run results (§6)
```

Mutation env var: `SG_AWS__LAB__ALLOW_MUTATIONS=1`. Tier-2 additionally requires an interactive `y/N` prompt (or `--tier-2-confirm` for scripted runs).

---

## 5. Tests (no mocks)

Unit tests under `tests/unit/sgraph_ai_service_playwright__cli/aws/lab/`. In-memory clients reuse the existing `*__In_Memory` pattern. Three categories:

- **Pure schema/enum tests** — type-safety, default values.
- **Ledger tests** — write/read/replay round-trip; partial write recovery; concurrent writers (file lock).
- **Runner tests** — `Lab__Runner__In_Memory` injects in-memory boto3 stubs and an in-memory ledger; runs experiments end-to-end; asserts teardown calls.

Integration tests under `tests/integration/sgraph_ai_service_playwright__cli/aws/lab/`:

- **`test_safety_kill_sigkill.py`** — see §4 step 8 of the safety doc. Gated.
- **`test_E11_propagation_timeline.py`** — runs E11 against a real lab zone, asserts propagation finishes within budget. Gated.
- Plus one minimal smoke test per Tier-2 experiment (with a long `pytest --timeout` budget).

---

## 6. Where it gets mounted

In `sg_compute/cli/Cli__SG.py`, alongside the existing `sg aws dns` mount:

```python
from sgraph_ai_service_playwright__cli.aws.lab.cli.Cli__Lab import lab_app

aws_app.add_typer(lab_app, name='lab')
```

So `sg aws lab list`, `sg aws lab run E11`, etc.

---

## 7. Estimated size

| Area | Files | Approx. lines |
|------|------:|--------------:|
| Schemas + enums + primitives + collections | ~22 | ~600 |
| Service (runner, ledger, sweeper, teardown, renderers) | ~14 | ~1200 |
| Experiments (~24 of them) | 24 | ~3000 (avg 125 lines each) |
| Temp boto3 clients | 2 | ~250 |
| In-tree lab Lambdas | 3 | ~150 |
| CLI | 1 | ~600 |
| Tests | ~30 | ~2000 |
| **Total** | ~96 | ~7800 |

Comparable to (slightly smaller than) the `sg aws dns` surface. Most of it is small files following identical templates — the experiments are highly regular.
