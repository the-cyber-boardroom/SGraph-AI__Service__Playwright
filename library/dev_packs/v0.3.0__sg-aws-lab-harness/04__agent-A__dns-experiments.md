---
title: "04 — Agent A — DNS experiments (P0+P1)"
file: 04__agent-A__dns-experiments.md
author: Architect (Claude)
date: 2026-05-17 (rev 3 — after DNS package deep-dive)
parent: README.md
size: S (small) — ~700 prod lines, ~400 test lines, ~1.5 days  (smaller than rev 2 because the dns/ package already does more than rev 2 credited)
depends_on: Foundation PR (02__common-foundation.md)
mandatory_reading:
  - team/humans/dinis_cruz/claude-code-web/05/17/00/v0.2.23__plan__vault-publish-spec/03__delta-from-lab-brief.md  # §B.1 — §B.7 — non-negotiable lab-brief corrections
delivers: lab P0 + lab P1 from lab-brief/07
---

# Agent A — DNS experiments

The smallest slice. The most valuable slice. Lands answers to Q1 + Q2 (the v2 brief's two biggest claims).

---

## What you own

**Folder:** `sgraph_ai_service_playwright__cli/aws/lab/service/experiments/dns/`

**Files to create** (per `lab-brief/05 §1` — but **filenames are CORRECTED per delta `B.3`**: no `E01__` numeric prefix; each file is named after its class):

| File | Tier | Experiment |
|------|------|------------|
| `Lab__Experiment__Zone_Inventory.py` | 0 (read-only) | Show NS set, record counts, existing wildcards |
| `Lab__Experiment__Resolver_Latency.py` | 0 | 8-public-resolver dig latency baseline |
| `Lab__Experiment__Authoritative_NS_Latency.py` | 0 | Per-NS SOA latency |
| `Lab__Experiment__Wildcard_Pre_Check.py` | 0 | What resolvers return for a not-yet-created name |
| `Lab__Experiment__InSync_Distribution.py` | 1 (mutating-low) | Q2 — `ChangeInfo` PENDING→INSYNC distribution |
| `Lab__Experiment__Propagation_Timeline.py` | 1 | Q2+Q1 — per-resolver first-correct time after INSYNC |
| `Lab__Experiment__Wildcard_Vs_Specific.py` | 1 | Q1 — specific-record-beats-wildcard |
| `Lab__Experiment__TTL_Respect.py` | 1 | Do public resolvers respect declared TTL? |
| `Lab__Experiment__Delete_Propagation.py` | 1 | How long after `delete_record` do resolvers return NXDOMAIN? |

The numeric IDs (`E01`, `E02`, ...) are preserved in each experiment's `name` attribute and surfaced via `sg aws lab list`, but they do NOT appear in filenames. (Source ordering inside the directory is by class name — that's fine.)

**Plus (the only NEW code beyond the existing dns/ package):**
- `service/teardown/Lab__Teardown__R53.py` — **thin wrapper around `Route53__AWS__Client.delete_record` and `batch_delete_records`.** Idempotency = re-read before delete. ~50 lines.
- `schemas/Schema__Lab__Result__DNS__*.py` — one file per result shape. **Compose `Schema__Dig__Result`, `Schema__Dns__Check__Result`, `Schema__Route53__Change__Result` (existing) — don't redefine.** Per delta `B.1` and `B.4`: no `Set__Str` / `Dict__Str__Str` / `Dict__Str__Int` field types — use `Type_Safe__Dict__Safe_Str__Safe_Str` collection subclasses with their own files under `collections/`.
- `service/renderers/Render__Timeline__ASCII.py` — fill in the `render_event_list(...)` body (foundation ships the stub)
- `service/Lab__Rate__Limiter__R53.py` — Route 53 mutations rate-limit (5/s/zone). The dns/ package does NOT have one today; the lab adds it. ~30 lines. (May be promoted to `_shared/` later if other surfaces need it.)
- `service/Lab__TEST_NET__Validator.py` — validates A-record values are in 192.0.2.0/24 / 198.51.100.0/24 / 203.0.113.0/24; the dns/ package does NOT enforce this. ~20 lines. (Promotable to `_shared/`.)
- `service/Lab__Propagation__Poller.py` — the actual lab value-add. Polls `Route53__Public_Resolver__Checker.check(...)` every 2s with timestamps; records per-resolver first-correct time. ~60 lines.
- Registration lines in `service/experiments/registry.py` (9 entries)
- For each `READ_ONLY` experiment (4 of them), a one-liner registration in `Lab__Source__Adapter` so the experiment appears in `sg aws observe sources` (per Decision #10).

The MISSING capabilities (from the deep-dive) the lab adds: (1) **propagation-timing measurement** — the dns/ package has one-shot checks only; lab adds the poll-with-timestamps wrapper. (2) **Route 53 rate limiting**. (3) **TEST-NET enforcement**. That's it. Everything else is reused.

**Experiment-class shape — per delta `B.2`:**

```python
# Lab__Experiment__Zone_Inventory.py
class Lab__Experiment__Zone_Inventory(Lab__Experiment):
    name           : Safe_Str__Lab__Experiment_Name = 'zone-inventory'
    tier           : Enum__Lab__Tier                = Enum__Lab__Tier.READ_ONLY
    budget_seconds : int                            = 30
    runner         : Lab__Runner                                          # injected at setup, NOT a parameter to execute()
    zone           : Safe_Str__DNS__Zone

    def setup(self, runner: Lab__Runner, zone: str) -> 'Self':
        self.runner = runner
        self.zone   = zone
        return self

    def execute(self) -> Schema__Lab__Run__Result:                        # no runner parameter
        ...
```

---

## What you do NOT touch

- Any file under `experiments/cf/`, `experiments/lambda_/`, `experiments/transition/`
- `Lab__Teardown__{CF,Lambda,ACM,EC2,SSM,IAM}.py` — those stay stubbed (other agents fill in)
- `aws/cf/` and `aws/lambda_/` packages — DNS primitive expansion is **not** in scope for this slice
- The `serve`, `runs diff`, HTML viewer — those are Agent E

---

## Reuse, don't rewrite — the DNS package gives you almost everything

A code-level deep-dive on `sgraph_ai_service_playwright__cli/aws/dns/` (2026-05-17) found that the existing package already provides every primitive these experiments need. **Reuse the package; add only the propagation-timing layer, the TEST-NET enforcement, and the Route 53 rate limiter.**

### Services (`aws/dns/service/`)

| Existing class | Surface | Why it matters for the experiments |
|---------------|---------|-----------------------------------|
| `Route53__AWS__Client` | `list_hosted_zones / find_hosted_zone_by_name / resolve_default_zone / get_hosted_zone / resolve_zone_id / list_records / get_record / create_record / upsert_record / delete_record / upsert_a_alias_record / batch_delete_records / get_change / wait_for_change(change_id, timeout=120, poll_interval=2, on_poll=None)` | **`wait_for_change(...)` with an `on_poll` callback already exists** — E10 (INSYNC distribution) and E11 (propagation timeline) both reuse it directly. `batch_delete_records(...)` is the primitive for `Lab__Teardown__R53`. `upsert_a_alias_record(...)` is what E27 needs when the lab creates wildcard ALIAS → CF. |
| `Route53__Authoritative__Checker` | `get_ns_for_zone(zone_id)` (auto-discovers 4 NS), `check(zone_id, name, rtype, expected='')` (unanimous-agreement check) | E03 (`authoritative-ns-latency`) reuses `get_ns_for_zone` directly; lab adds per-NS timing on top of `Schema__Dig__Result.duration_ms` (which is already captured per query). |
| `Route53__Public_Resolver__Checker` | `check(name, rtype, expected='')` with 6-resolver smart-verify default; `.use_full_set(quorum=0)` switches to all 8 | **Answers open Q5 already.** E02 (`resolver-latency`), E11 (`propagation-timeline`), E12 (`wildcard-vs-specific`), E13 (`ttl-respect`), E14 (`delete-propagation`) all reuse `.check()`. The 6-vs-8 toggle is built-in. |
| `Route53__Smart_Verify` | `decide_before_add → Schema__Smart_Verify__Decision` (NEW_NAME / UPSERT / DELETE); `verify_after_mutation → Schema__Smart_Verify__Result` | **Cache-pollution-aware safety logic the lab gets for free.** E12 should call `decide_before_add` before mutating to know whether to skip the public-resolver check (already knows about TTL holdover). |
| `Route53__Check__Orchestrator` | `check_authoritative / check_public_resolvers / check_local` | Use this directly from `Lab__Runner.dns_check()` accessor. |
| `Route53__Local__Checker` | host's default resolver | (Lab probably doesn't use this — cache-polluting; experiments target authoritative + public.) |
| `Dig__Runner` | `run(nameserver, name, rtype, no_recurse=False, timeout=5) → Schema__Dig__Result`; per-query timing already in result; `check_available() -> bool` | Reused indirectly via the three checker classes. Lab does not call `Dig__Runner.run()` itself. |
| `Route53__Zone__Resolver` | `resolve_zone_for_fqdn(fqdn) → Schema__Route53__Hosted_Zone` (walks labels longest-first, including the FQDN itself) | E01 (`zone-inventory`) uses this for "given an FQDN, which zone owns it?". |
| `Route53__Instance__Linker` | `resolve_instance / resolve_latest / get_public_ip / get_name_tag` | E27 (full cold-path; Agent D) uses `resolve_latest()` to baseline against an existing vault-app EC2. |

### Schemas (`aws/dns/schemas/`) — compose, don't recreate

| Existing schema | Lab use |
|----------------|---------|
| `Schema__Route53__Hosted_Zone` (zone_id, name, private_zone, record_count, comment, caller_reference) | Field in `Schema__Lab__Result__DNS__Zone_Inventory` |
| `Schema__Route53__Record` (name, record_type, ttl, values, alias_target, set_identifier) | Field in lab results that capture record state |
| `Schema__Route53__Change__Result` (change_id, status, submitted_at) | Field in `Schema__Lab__Result__DNS__InSync_Sample` |
| `Schema__Dig__Result` (nameserver, name, rtype, values, exit_code, error, **duration_ms**) | **`duration_ms` is the lab's per-query timing.** Compose into lab results, don't add another timing field. |
| `Schema__Dns__Check__Result` (mode, name, rtype, expected, results, passed, agreed_count, total_count) | Field in `Schema__Lab__Result__DNS__Propagation` per poll |
| `Schema__Smart_Verify__Decision`, `Schema__Smart_Verify__Result` | E12 reuses to decide whether public-resolver polling is safe |

### Enums (`aws/dns/enums/`) — reuse directly

- `Enum__Route53__Record_Type` (A, AAAA, CNAME, MX, TXT, NS, SOA, PTR, SRV, CAA) — every lab experiment that takes a record type uses this; do NOT add `Enum__Lab__Record_Type`.
- `Enum__Dns__Resolver` (with `.smart_verify_subset()` and `.full_set()` class methods) — the canonical resolver list.
- `Enum__Dns__Check__Mode` (AUTHORITATIVE, PUBLIC_RESOLVERS, LOCAL) — reuse.
- `Enum__Smart_Verify__Decision` (NEW_NAME, UPSERT, DELETE) — reuse.

### Primitives (`aws/dns/primitives/`) — reuse directly

- `Safe_Str__Hosted_Zone_Id` (strips `/hostedzone/` prefix, enforces `Z` + alphanumeric)
- `Safe_Str__Record_Name` (RFC 1035 multi-label, wildcard `*` allowed)
- `Safe_Int__TTL` (1..2147483647, default=300)
- `Safe_Str__Domain_Name`

**Do not add** `Safe_Str__DNS__Zone` or similar — `Safe_Str__Hosted_Zone_Id` and `Safe_Str__Domain_Name` cover the lab's needs.

### Tests — follow `_Fake_Route53__AWS__Client` + canned-data pattern

The DNS package tests use real subclasses with stub boto3 clients (no mocks framework, all canned data at module level). Examples to model after:

- `tests/unit/sgraph_ai_service_playwright__cli/aws/dns/test_Route53__AWS__Client.py` — `_Fake_Route53__AWS__Client` overriding `client()` to return `_Fake_Route53_Boto3_Client` with canned zones/records/changes and a scripted PENDING→INSYNC sequence
- `test_Dig__Runner.py` — `_Fake_Dig__Runner` with `_FakeCompleted` subprocess stub returning canned stdout

Lab tests follow the same shape: `_Fake_Lab__Runner` subclass + `_Fake_Route53__AWS__Client` reused from the existing dns tests.

---

## Acceptance

Run from a fresh checkout of the integration branch with the Foundation PR merged:

```bash
# read-only — no env vars
sg aws lab list                                                                # 9 DNS experiments visible
sg aws lab run zone-inventory          --zone sg-compute.sgraph.ai             # by experiment name
sg aws lab run resolver-latency        google.com
sg aws lab run authoritative-ns-latency sg-compute.sgraph.ai
sg aws lab run wildcard-pre-check      not-yet-created.sg-compute.sgraph.ai

# mutating
SG_AWS__LAB__ALLOW_MUTATIONS=1 sg aws lab run insync-distribution --repeat 5
SG_AWS__LAB__ALLOW_MUTATIONS=1 sg aws lab run propagation-timeline --ttl 60
SG_AWS__LAB__ALLOW_MUTATIONS=1 sg aws lab run wildcard-vs-specific
SG_AWS__LAB__ALLOW_MUTATIONS=1 sg aws lab run delete-propagation

# verify clean
sg aws lab sweep                                      # → "no leaked resources"
```

(The CLI accepts either the experiment `name` — `zone-inventory` — or the numeric ID — `E01` — both resolve via the registry. The `name` form is the public surface.)

**Plus** unit tests under `tests/unit/sgraph_ai_service_playwright__cli/aws/lab/experiments/dns/` pass:

```bash
pytest tests/unit/sgraph_ai_service_playwright__cli/aws/lab/experiments/dns/ -v
```

**Plus** the safety acceptance (DNS-scoped slice of `lab-brief/04 §8`):

```bash
SG_AWS__LAB__ALLOW_MUTATIONS=1 SG_AWS__LAB__DESTROY_TEST=1 \
  pytest tests/integration/sgraph_ai_service_playwright__cli/aws/lab/test_safety_dns.py
```

---

## Risks to watch

- **Rate limits.** Route 53 mutations cap at 5/s/zone. Your `Lab__Rate__Limiter__R53` must be honoured by every mutation in your experiments. E10 `--repeat 20` is the failure case if you don't.
- **TEST-NET enforcement.** Every A-record VALUE you write must be in `192.0.2.0/24`, `198.51.100.0/24`, or `203.0.113.0/24` unless the caller passed `--force-real-ip`. `Lab__Runner.create_and_register(...)` should refuse a non-TEST-NET value via `Lab__TEST_NET__Validator`.
- **Wildcard interference.** E12 (`wildcard-vs-specific`) might run in a zone where another wildcard already exists. Detect this via `Route53__AWS__Client.get_record(zone, "*.<zone>", "A")`, refuse to overwrite a non-lab wildcard, and document `--wildcard-already-present` in the CLI help.
- **Public-resolver cache pollution.** E11/E12 spray TEST-NET addresses into public resolver caches. That's the point. Use unique per-run record names (`lab-prop-<run-id>.<zone>`) so no two runs collide.
- **Sequential checker calls — opt-in parallelism.** `Route53__Public_Resolver__Checker.check(...)` is sequential (no `ThreadPoolExecutor`) today. For E11 / E12 / E14 propagation-timeline experiments, the **per-poll** dig fan-out can stay sequential (we measure first-correct time per resolver, not aggregate timing) — but if a future experiment needs true-parallel fan-out, propose adding a `parallel=True` opt-in to `Route53__Public_Resolver__Checker` rather than forking the class.
- **Don't duplicate `Smart_Verify` logic.** When E12 needs to know "is this a NEW_NAME or UPSERT?", call `Route53__Smart_Verify.decide_before_add(...)`; do not re-implement the get-record + classify pattern.

### Operator-visible side effects (document in CLI `--help`)

Two characteristics of "measure real AWS behaviour" that operators of other `sg aws *` commands need to know about. Surface these prominently in `sg aws lab run --help` and in each mutating experiment's `show` output:

- **Public-resolver cache pollution.** Mutating experiments (E11/E12/E14) intentionally spray TEST-NET addresses (192.0.2.x, 198.51.100.x, 203.0.113.x) into the caches of the 6-8 public resolvers (Cloudflare, Google, Quad9, AdGuard, OpenDNS). Per-run record names (`lab-prop-<run-id>.<zone>`) ensure no two lab runs collide, but **a subsequent `sg aws dns records check --public-resolvers <name>` for the same record name will see the lab's poisoned cache until the TTL expires**. The lab's pre-mutation use of `Route53__Smart_Verify.decide_before_add` already documents prior-TTL skip semantics for the same reason.
- **Route 53 rate-limit consumption.** R53 caps mutations at 5/s/zone account-wide. `Lab__Rate__Limiter__R53` throttles only lab calls — it does NOT coordinate with concurrent `sg aws dns records add/update/delete` invocations against the same zone. Operators running a lab mutating experiment AND `sg aws dns *` mutations against the same zone may both see `ThrottlingException`. Document loudly; recommend lab mutating experiments target a dedicated zone (per Q1 RESOLVED — post-v2 `lab.sg-labs.app`) or run during quiet windows pre-v2.

---

## Commit + PR

Branch: `claude/aws-primitives-support-NVyEh-dns`

Commit messages follow the repo style — `feat(v0.2.28): lab agent-A — DNS experiments (P0+P1)`. Bullet the experiments shipped + the kill-9 result.

Open PR against `claude/aws-primitives-support-NVyEh` (integration branch). Tag the Opus coordinator. Do **not** merge yourself.
