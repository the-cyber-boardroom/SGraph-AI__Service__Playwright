#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════════════════════════
# sg-lab — MVP harness for the sg aws lab brief
# ═══════════════════════════════════════════════════════════════════════════════
# A single-file, dependency-light, working slice of the harness described in
# /home/claude/work/lab-brief/. Demonstrates:
#
#   - The Lab__Runner / Lab__Ledger / experiment dispatch pattern.
#   - Three runnable Tier-0 experiments (E02, E03 — read-only DNS measurements).
#   - The Schema__Lab__Run__Result shape and four output forms (table, ASCII
#     timeline, JSON, status code).
#   - The atexit + signal safety net (no-op for Tier-0 but wired in).
#   - The .sg-lab/ directory layout.
#
# This MVP intentionally does NOT include:
#   - AWS-mutating experiments (Tier-1 / Tier-2) — they require AWS credentials.
#   - The Type_Safe / osbot-utils integration — those land in the real harness;
#     this MVP uses dataclasses + light validation so the file is runnable
#     anywhere.
#   - The Lab__Sweeper — only meaningful once Tier-1 experiments exist.
#
# What it proves:
#   - The harness shape is sound.
#   - One can add an experiment in ~30 lines and get four output forms for free.
#   - The ledger format works end-to-end.
#   - Real DNS measurements come out as expected.
#
# Run:
#   python sg_lab_mvp.py list
#   python sg_lab_mvp.py run E02 --name google.com
#   python sg_lab_mvp.py run E03 --zone sgraph.ai
#   python sg_lab_mvp.py run E02 --name google.com --json
#   python sg_lab_mvp.py runs list
#   python sg_lab_mvp.py runs show <run-id>
# ═══════════════════════════════════════════════════════════════════════════════

import argparse
import atexit
import dataclasses
import datetime
import json
import os
import pathlib
import secrets
import signal
import socket
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional

try:
    import dns.resolver
    import dns.exception
    HAS_DNSPYTHON = True
except ImportError:
    HAS_DNSPYTHON = False


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

SG_LAB_HOME = pathlib.Path(os.environ.get('SG_LAB_HOME', '.sg-lab'))

# Public-resolver smart-verify set — mirrors Enum__Dns__Resolver.smart_verify_subset()
PUBLIC_RESOLVERS: List[Dict[str, str]] = [
    {'name': 'Cloudflare 1.1.1.1', 'ip': '1.1.1.1'        },
    {'name': 'Cloudflare 1.0.0.1', 'ip': '1.0.0.1'        },
    {'name': 'Google 8.8.8.8'    , 'ip': '8.8.8.8'        },
    {'name': 'Google 8.8.4.4'    , 'ip': '8.8.4.4'        },
    {'name': 'Quad9 9.9.9.9'     , 'ip': '9.9.9.9'        },
    {'name': 'AdGuard EU'        , 'ip': '94.140.14.14'   },
]

ANSI = {
    'reset' : '\033[0m'  ,
    'bold'  : '\033[1m'  ,
    'dim'   : '\033[2m'  ,
    'red'   : '\033[31m' ,
    'green' : '\033[32m' ,
    'yellow': '\033[33m' ,
    'blue'  : '\033[34m' ,
    'cyan'  : '\033[36m' ,
    'gray'  : '\033[90m' ,
}

def c(s: str, color: str) -> str:
    if not sys.stdout.isatty():
        return s
    return f'{ANSI[color]}{s}{ANSI["reset"]}'


# ─────────────────────────────────────────────────────────────────────────────
# Schemas — the structured result shapes
# ─────────────────────────────────────────────────────────────────────────────

@dataclasses.dataclass
class Schema__Lab__Resolver__Observation:
    """One probe of one resolver at one time."""
    resolver_name : str
    resolver_ip   : str
    name          : str
    rtype         : str
    values        : List[str]
    rcode         : str        # NOERROR | NXDOMAIN | TIMEOUT | SERVFAIL | ERROR
    duration_ms   : int
    error         : str = ''


@dataclasses.dataclass
class Schema__Lab__Timing__Sample:
    """One stopwatch reading."""
    label       : str
    duration_ms : int
    started_at  : str          # ISO 8601 UTC
    ended_at    : str          # ISO 8601 UTC


@dataclasses.dataclass
class Schema__Lab__Ledger__Entry:
    """One mutable AWS resource the harness created and will tear down."""
    run_id         : str
    entry_id       : str
    created_at     : str
    expires_at     : str
    resource_type  : str       # R53_RECORD | CF_DISTRIBUTION | LAMBDA | …
    resource_id    : str
    cleanup_payload: Dict[str, Any]
    teardown_order : int       # smaller-first on cleanup
    state          : str       # PENDING | DELETED | FAILED | ABANDONED


@dataclasses.dataclass
class Schema__Lab__Run__Result:
    """The canonical contract every experiment produces."""
    run_id          : str
    experiment_id   : str
    experiment_name : str
    tier            : str
    started_at      : str
    ended_at        : str
    status          : str                                                                  # PENDING | RUNNING | OK | FAILED | TIMEOUT | ABORTED
    params          : Dict[str, Any]
    timings         : List[Schema__Lab__Timing__Sample]
    observations    : List[Schema__Lab__Resolver__Observation]
    summary         : Dict[str, Any]                                                       # experiment-specific top-level numbers
    cleanup         : Dict[str, Any]                                                       # ledger_entries / deleted / failed
    error           : str = ''


# ─────────────────────────────────────────────────────────────────────────────
# Ledger — append-only JSONL with crash safety
# ─────────────────────────────────────────────────────────────────────────────

class Lab__Ledger:
    """Per-run append-only JSONL ledger. The single source of truth for cleanup."""

    def __init__(self, run_id: str, base: pathlib.Path = SG_LAB_HOME):
        self.run_id   = run_id
        self.base     = base
        self.path     = base / 'ledger' / f'{run_id}.jsonl'
        self._entries : List[Schema__Lab__Ledger__Entry] = []
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, entry: Schema__Lab__Ledger__Entry) -> None:
        self._entries.append(entry)
        with self.path.open('a') as f:
            f.write(json.dumps(dataclasses.asdict(entry)) + '\n')
            f.flush()
            os.fsync(f.fileno())                                                            # crash-safe — must be on disk before AWS call

    def update(self, entry: Schema__Lab__Ledger__Entry) -> None:
        # Append a new line representing the update. On read, last-wins per entry_id.
        with self.path.open('a') as f:
            f.write(json.dumps(dataclasses.asdict(entry)) + '\n')
            f.flush()
            os.fsync(f.fileno())

    def pending_entries(self) -> List[Schema__Lab__Ledger__Entry]:
        # Read-back with last-wins semantics by entry_id
        latest: Dict[str, Schema__Lab__Ledger__Entry] = {}
        if not self.path.exists():
            return []
        with self.path.open() as f:
            for line in f:
                d = json.loads(line)
                e = Schema__Lab__Ledger__Entry(**d)
                latest[e.entry_id] = e
        return [e for e in latest.values() if e.state == 'PENDING']

    def has_pending(self) -> bool:
        return len(self.pending_entries()) > 0


# ─────────────────────────────────────────────────────────────────────────────
# Timing helpers
# ─────────────────────────────────────────────────────────────────────────────

def utc_now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

def utc_now_iso_ms() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ')

def make_run_id() -> str:
    ts = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H-%M-%SZ')
    nonce = secrets.token_hex(3)
    return f'{ts}__{nonce}'


class Stopwatch:
    def __init__(self, label: str):
        self.label      = label
        self.started_at = ''
        self.ended_at   = ''
        self._t0        = 0.0
        self.duration_ms = 0

    def __enter__(self):
        self.started_at = utc_now_iso_ms()
        self._t0        = time.perf_counter()
        return self

    def __exit__(self, *exc):
        elapsed_s        = time.perf_counter() - self._t0
        self.duration_ms = int(elapsed_s * 1000)
        self.ended_at    = utc_now_iso_ms()

    def to_sample(self) -> Schema__Lab__Timing__Sample:
        return Schema__Lab__Timing__Sample(label       = self.label      ,
                                            duration_ms = self.duration_ms,
                                            started_at  = self.started_at ,
                                            ended_at    = self.ended_at   )


# ─────────────────────────────────────────────────────────────────────────────
# DNS probe — replaces Dig__Runner for the MVP
# ─────────────────────────────────────────────────────────────────────────────

class Dns__Probe:
    """Portable replacement for `dig` using dnspython. Same shape as Dig__Runner."""

    def __init__(self, timeout: float = 3.0):
        self.timeout = timeout

    def query_at(self, resolver_ip: str, name: str, rtype: str = 'A') -> Schema__Lab__Resolver__Observation:
        if not HAS_DNSPYTHON:
            return Schema__Lab__Resolver__Observation(
                resolver_name = resolver_ip                  ,
                resolver_ip   = resolver_ip                  ,
                name          = name                         ,
                rtype         = rtype                        ,
                values        = []                           ,
                rcode         = 'ERROR'                      ,
                duration_ms   = 0                            ,
                error         = 'dnspython not installed'    ,
            )

        r = dns.resolver.Resolver(configure=False)
        r.nameservers = [resolver_ip]
        r.timeout = self.timeout
        r.lifetime = self.timeout

        t0 = time.perf_counter()
        try:
            ans = r.resolve(name, rtype)
            duration_ms = int((time.perf_counter() - t0) * 1000)
            values = [str(rr) for rr in ans]
            return Schema__Lab__Resolver__Observation(
                resolver_name = resolver_ip ,
                resolver_ip   = resolver_ip ,
                name          = name        ,
                rtype         = rtype       ,
                values        = values      ,
                rcode         = 'NOERROR'   ,
                duration_ms   = duration_ms ,
            )
        except dns.resolver.NXDOMAIN:
            duration_ms = int((time.perf_counter() - t0) * 1000)
            return Schema__Lab__Resolver__Observation(
                resolver_name = resolver_ip ,
                resolver_ip   = resolver_ip ,
                name          = name        ,
                rtype         = rtype       ,
                values        = []          ,
                rcode         = 'NXDOMAIN'  ,
                duration_ms   = duration_ms ,
            )
        except dns.exception.Timeout:
            duration_ms = int((time.perf_counter() - t0) * 1000)
            return Schema__Lab__Resolver__Observation(
                resolver_name = resolver_ip                ,
                resolver_ip   = resolver_ip                ,
                name          = name                       ,
                rtype         = rtype                      ,
                values        = []                         ,
                rcode         = 'TIMEOUT'                  ,
                duration_ms   = duration_ms                ,
                error         = f'timed out after {self.timeout}s',
            )
        except Exception as exc:
            duration_ms = int((time.perf_counter() - t0) * 1000)
            return Schema__Lab__Resolver__Observation(
                resolver_name = resolver_ip   ,
                resolver_ip   = resolver_ip   ,
                name          = name          ,
                rtype         = rtype         ,
                values        = []            ,
                rcode         = 'ERROR'       ,
                duration_ms   = duration_ms   ,
                error         = str(exc)      ,
            )


# ─────────────────────────────────────────────────────────────────────────────
# Lab__Runner — the harness's central object
# ─────────────────────────────────────────────────────────────────────────────

class Lab__Runner:
    def __init__(self, run_id: Optional[str] = None, base: pathlib.Path = SG_LAB_HOME):
        self.run_id = run_id or make_run_id()
        self.base   = base
        self.ledger = Lab__Ledger(self.run_id, base)
        self.dns    = Dns__Probe()
        self._safety_net_installed = False

    def install_safety_net(self) -> None:
        if self._safety_net_installed:
            return
        atexit.register(self._emergency_teardown)
        try:
            signal.signal(signal.SIGINT , self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
        except Exception:
            pass                                                                            # non-main-thread can't set signals; OK for nested
        self._safety_net_installed = True

    def _emergency_teardown(self) -> None:
        if not self.ledger.has_pending():
            return
        sys.stderr.write(c('\n[SAFETY] Emergency teardown — ledger has pending entries.\n', 'yellow'))
        # In the full harness, this dispatches to Lab__Teardown__Dispatcher.
        # The MVP does Tier-0 experiments only, so this branch is unreachable in
        # the demo, but the hook is wired in so the shape is real.

    def _signal_handler(self, signum, frame):
        sys.stderr.write(c(f'\n[SAFETY] Signal {signum} received.\n', 'yellow'))
        self._emergency_teardown()
        sys.exit(130 if signum == signal.SIGINT else 143)

    def write_result(self, result: Schema__Lab__Run__Result) -> pathlib.Path:
        d = self.base / 'runs' / self.run_id
        d.mkdir(parents=True, exist_ok=True)
        out = d / 'result.json'
        with out.open('w') as f:
            json.dump(dataclasses.asdict(result), f, indent=2)
        return out

    def stopwatch(self, label: str) -> Stopwatch:
        return Stopwatch(label)


# ─────────────────────────────────────────────────────────────────────────────
# Experiments — each one a class with execute(runner) -> Schema__Lab__Run__Result
# ─────────────────────────────────────────────────────────────────────────────

class Lab__Experiment:
    id            : str = ''
    name          : str = ''
    tier          : str = 'READ_ONLY'                                                       # READ_ONLY | MUTATING_LOW | MUTATING_HIGH
    description   : str = ''
    budget_seconds: int = 60

    def execute(self, runner: Lab__Runner, params: Dict[str, Any]) -> Schema__Lab__Run__Result:
        raise NotImplementedError

    @classmethod
    def metadata(cls) -> Dict[str, Any]:
        return {'id': cls.id, 'name': cls.name, 'tier': cls.tier, 'description': cls.description, 'budget_seconds': cls.budget_seconds}


# ─── E02 — resolver-latency ──────────────────────────────────────────────────

class E02__Resolver_Latency(Lab__Experiment):
    id          = 'E02'
    name        = 'dns resolver-latency'
    tier        = 'READ_ONLY'
    description = 'Probe N public resolvers for a known stable record; report per-resolver latency.'
    budget_seconds = 30

    def execute(self, runner: Lab__Runner, params: Dict[str, Any]) -> Schema__Lab__Run__Result:
        started_at  = utc_now_iso()
        name        = params.get('name', 'google.com')
        rtype       = params.get('rtype', 'A')
        repeat      = int(params.get('repeat', 1))

        observations: List[Schema__Lab__Resolver__Observation] = []
        timings     : List[Schema__Lab__Timing__Sample] = []

        with runner.stopwatch('total') as sw_total:
            for iteration in range(repeat):
                with ThreadPoolExecutor(max_workers=len(PUBLIC_RESOLVERS)) as pool:
                    futs = {
                        pool.submit(runner.dns.query_at, r['ip'], name, rtype): r
                        for r in PUBLIC_RESOLVERS
                    }
                    for fut in as_completed(futs):
                        r   = futs[fut]
                        obs = fut.result()
                        obs.resolver_name = r['name']
                        observations.append(obs)

        timings.append(sw_total.to_sample())

        # Summary stats — per resolver, aggregated across repeats
        per_resolver: Dict[str, List[int]] = {}
        for obs in observations:
            per_resolver.setdefault(obs.resolver_name, []).append(obs.duration_ms)

        summary: Dict[str, Any] = {
            'name'        : name                                                            ,
            'rtype'       : rtype                                                           ,
            'repeat'      : repeat                                                          ,
            'total_probes': len(observations)                                               ,
            'per_resolver': {
                rname: {
                    'min_ms'   : min(samples)                          ,
                    'max_ms'   : max(samples)                          ,
                    'median_ms': sorted(samples)[len(samples)//2]      ,
                    'samples'  : samples                               ,
                }
                for rname, samples in per_resolver.items()
            }                                                                               ,
        }

        return Schema__Lab__Run__Result(
            run_id          = runner.run_id                                                 ,
            experiment_id   = self.id                                                       ,
            experiment_name = self.name                                                     ,
            tier            = self.tier                                                     ,
            started_at      = started_at                                                    ,
            ended_at        = utc_now_iso()                                                 ,
            status          = 'OK'                                                          ,
            params          = params                                                        ,
            timings         = timings                                                       ,
            observations    = observations                                                  ,
            summary         = summary                                                       ,
            cleanup         = {'ledger_entries': 0, 'deleted': 0, 'failed': 0}              ,
        )


# ─── E03 — authoritative-ns-latency ──────────────────────────────────────────

class E03__Authoritative_NS_Latency(Lab__Experiment):
    id          = 'E03'
    name        = 'dns authoritative-ns-latency'
    tier        = 'READ_ONLY'
    description = "Find a zone's NS set (by querying it), then probe each NS in parallel for SOA."
    budget_seconds = 30

    def execute(self, runner: Lab__Runner, params: Dict[str, Any]) -> Schema__Lab__Run__Result:
        started_at = utc_now_iso()
        zone       = params.get('zone', 'sgraph.ai')

        observations: List[Schema__Lab__Resolver__Observation] = []
        timings     : List[Schema__Lab__Timing__Sample] = []

        # Step 1: NS lookup — ask a public resolver for the zone's NS set
        with runner.stopwatch('ns-discovery') as sw_ns:
            ns_obs = runner.dns.query_at('1.1.1.1', zone, 'NS')
        timings.append(sw_ns.to_sample())

        ns_names = ns_obs.values if ns_obs.rcode == 'NOERROR' else []

        # Step 2: Resolve each NS hostname to IP
        ns_ips: List[Dict[str, str]] = []
        for ns_name in ns_names:
            ns_name_clean = str(ns_name).rstrip('.')
            try:
                ip = socket.gethostbyname(ns_name_clean)
                ns_ips.append({'name': ns_name_clean, 'ip': ip})
            except Exception:
                continue

        # Step 3: Probe each NS for SOA in parallel
        with runner.stopwatch('soa-probe-fanout') as sw_soa:
            if ns_ips:
                with ThreadPoolExecutor(max_workers=len(ns_ips)) as pool:
                    futs = {
                        pool.submit(runner.dns.query_at, ns['ip'], zone, 'SOA'): ns
                        for ns in ns_ips
                    }
                    for fut in as_completed(futs):
                        ns  = futs[fut]
                        obs = fut.result()
                        obs.resolver_name = ns['name']
                        observations.append(obs)
        timings.append(sw_soa.to_sample())

        # Extract SOA serials for consistency check
        serials: List[str] = []
        for obs in observations:
            for v in obs.values:
                # SOA format: "ns. hostmaster. SERIAL refresh retry expire minimum"
                parts = str(v).split()
                if len(parts) >= 3:
                    serials.append(parts[2])

        all_agree = len(set(serials)) == 1 if serials else False

        summary: Dict[str, Any] = {
            'zone'             : zone                                  ,
            'ns_count'         : len(ns_names)                         ,
            'ns_names'         : [str(n).rstrip('.') for n in ns_names],
            'all_ns_agree_soa' : all_agree                             ,
            'soa_serials'      : list(set(serials))                    ,
        }

        return Schema__Lab__Run__Result(
            run_id          = runner.run_id                                                 ,
            experiment_id   = self.id                                                       ,
            experiment_name = self.name                                                     ,
            tier            = self.tier                                                     ,
            started_at      = started_at                                                    ,
            ended_at        = utc_now_iso()                                                 ,
            status          = 'OK' if ns_names else 'FAILED'                                ,
            params          = params                                                        ,
            timings         = timings                                                       ,
            observations    = observations                                                  ,
            summary         = summary                                                       ,
            cleanup         = {'ledger_entries': 0, 'deleted': 0, 'failed': 0}              ,
            error           = '' if ns_names else 'No NS records returned'                  ,
        )


# ─── E04 — wildcard-pre-check ────────────────────────────────────────────────

class E04__Wildcard_Pre_Check(Lab__Experiment):
    id          = 'E04'
    name        = 'dns wildcard-pre-check'
    tier        = 'READ_ONLY'
    description = 'Probe a name against all public resolvers; show NXDOMAIN vs wildcard-match.'
    budget_seconds = 30

    def execute(self, runner: Lab__Runner, params: Dict[str, Any]) -> Schema__Lab__Run__Result:
        started_at = utc_now_iso()
        name       = params.get('name', 'doesnotexist-test-record.example.com')

        observations: List[Schema__Lab__Resolver__Observation] = []
        timings     : List[Schema__Lab__Timing__Sample] = []

        with runner.stopwatch('total') as sw_total:
            with ThreadPoolExecutor(max_workers=len(PUBLIC_RESOLVERS)) as pool:
                futs = {pool.submit(runner.dns.query_at, r['ip'], name, 'A'): r for r in PUBLIC_RESOLVERS}
                for fut in as_completed(futs):
                    r   = futs[fut]
                    obs = fut.result()
                    obs.resolver_name = r['name']
                    observations.append(obs)
        timings.append(sw_total.to_sample())

        # Categorise
        rcodes = [obs.rcode for obs in observations]
        nxdomain_count = rcodes.count('NXDOMAIN')
        noerror_count  = rcodes.count('NOERROR')
        timeout_count  = rcodes.count('TIMEOUT')

        # If everyone sees the same value(s), it's deterministic — possibly a wildcard
        all_values = sorted(set(tuple(sorted(obs.values)) for obs in observations if obs.values))

        summary: Dict[str, Any] = {
            'name'           : name           ,
            'nxdomain_count' : nxdomain_count ,
            'noerror_count'  : noerror_count  ,
            'timeout_count'  : timeout_count  ,
            'distinct_value_sets': [list(v) for v in all_values],
            'likely_wildcard': noerror_count >= len(PUBLIC_RESOLVERS) - 1 and len(all_values) == 1,
        }

        return Schema__Lab__Run__Result(
            run_id          = runner.run_id                                                 ,
            experiment_id   = self.id                                                       ,
            experiment_name = self.name                                                     ,
            tier            = self.tier                                                     ,
            started_at      = started_at                                                    ,
            ended_at        = utc_now_iso()                                                 ,
            status          = 'OK'                                                          ,
            params          = params                                                        ,
            timings         = timings                                                       ,
            observations    = observations                                                  ,
            summary         = summary                                                       ,
            cleanup         = {'ledger_entries': 0, 'deleted': 0, 'failed': 0}              ,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Registry
# ─────────────────────────────────────────────────────────────────────────────

EXPERIMENTS: Dict[str, Lab__Experiment] = {
    'E02': E02__Resolver_Latency()        ,
    'E03': E03__Authoritative_NS_Latency(),
    'E04': E04__Wildcard_Pre_Check()      ,
}


# ─────────────────────────────────────────────────────────────────────────────
# Renderers
# ─────────────────────────────────────────────────────────────────────────────

def render__list_experiments() -> str:
    rows = []
    rows.append(c(f'{"id":<6} {"name":<36} {"tier":<14} {"budget":<8}', 'bold'))
    rows.append('─' * 70)
    for exp in EXPERIMENTS.values():
        rows.append(f'{exp.id:<6} {exp.name:<36} {exp.tier:<14} {exp.budget_seconds}s')
    return '\n'.join(rows)


def render__result_table(result: Schema__Lab__Run__Result) -> str:
    lines = []
    bullet  = c('▾', 'cyan')
    diamond = c('◇', 'gray')
    status_color = 'green' if result.status == 'OK' else 'red'
    lines.append(f'{bullet} Lab Run  {diamond} {c(result.experiment_name, "bold")}  {diamond} run-id {c(result.run_id, "dim")}')
    lines.append(f'  experiment      {result.experiment_id}')
    lines.append(f'  tier            {result.tier}')
    lines.append(f'  status          {c(result.status, status_color)}')
    if result.error:
        lines.append(f'  error           {c(result.error, "red")}')
    if result.params:
        for k, v in result.params.items():
            lines.append(f'  param {k:<10}{v}')

    # Resolver observations table
    if result.observations:
        lines.append('')
        header = c(f'  {"resolver":<24} {"rcode":<10} {"latency":>10}   value(s)', 'bold')
        lines.append(header)
        lines.append('  ' + '─' * 66)
        for obs in result.observations:
            rcode_color = 'green' if obs.rcode == 'NOERROR' else 'yellow' if obs.rcode == 'NXDOMAIN' else 'red'
            values_str = ', '.join(obs.values[:3]) if obs.values else c('(none)', 'gray')
            if len(obs.values) > 3:
                values_str += f' (+{len(obs.values) - 3} more)'
            lines.append(f'  {obs.resolver_name:<24} {c(obs.rcode, rcode_color):<10}   {obs.duration_ms:>4} ms   {values_str}')

    # Timings
    if result.timings:
        lines.append('')
        lines.append(c('  Timings', 'bold'))
        for t in result.timings:
            lines.append(f'    {t.label:<24} {t.duration_ms:>5} ms')

    # Summary
    if result.summary:
        lines.append('')
        lines.append(c('  Summary', 'bold'))
        for k, v in result.summary.items():
            if isinstance(v, (dict, list)):
                lines.append(f'    {k:<24} {c(json.dumps(v, default=str)[:80], "gray")}')
            else:
                lines.append(f'    {k:<24} {v}')

    # Cleanup
    lines.append('')
    cl = result.cleanup
    cleanup_status = c('✓', 'green') if cl.get('failed', 0) == 0 else c('✗', 'red')
    lines.append(f'  cleanup         {cleanup_status} {cl.get("deleted", 0)}/{cl.get("ledger_entries", 0)} resources deleted')

    return '\n'.join(lines)


def render__ascii_timeline(result: Schema__Lab__Run__Result) -> str:
    if not result.observations:
        return '(no observations to plot)'
    lines = []
    lines.append(c('  Latency plot (one ▮ per 20 ms, capped at 60)', 'bold'))
    max_ms = max(obs.duration_ms for obs in result.observations) or 1
    for obs in sorted(result.observations, key=lambda o: o.duration_ms):
        bar_len = min(60, obs.duration_ms // 20)
        bar = '▮' * bar_len
        color = 'green' if obs.rcode == 'NOERROR' else 'yellow' if obs.rcode == 'NXDOMAIN' else 'red'
        lines.append(f'  {obs.resolver_name:<24}{c(bar, color):<60} {obs.duration_ms:>5} ms')
    return '\n'.join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def cmd_list(args):
    print(render__list_experiments())


def cmd_run(args):
    if args.experiment_id not in EXPERIMENTS:
        sys.stderr.write(c(f'Unknown experiment: {args.experiment_id}\n', 'red'))
        sys.stderr.write(f'Available: {", ".join(EXPERIMENTS.keys())}\n')
        sys.exit(2)

    exp = EXPERIMENTS[args.experiment_id]

    # Extra params parsed from --param key=value
    params: Dict[str, Any] = {}
    for spec in args.param or []:
        if '=' not in spec:
            sys.stderr.write(c(f'Bad --param: {spec} (expected key=value)\n', 'red'))
            sys.exit(2)
        k, v = spec.split('=', 1)
        params[k] = v
    # Common shortcuts
    if args.name:    params['name']   = args.name
    if args.zone:    params['zone']   = args.zone
    if args.rtype:   params['rtype']  = args.rtype
    if args.repeat:  params['repeat'] = args.repeat

    runner = Lab__Runner()
    runner.install_safety_net()

    try:
        result = exp.execute(runner, params)
    except Exception as exc:
        result = Schema__Lab__Run__Result(
            run_id          = runner.run_id   ,
            experiment_id   = exp.id          ,
            experiment_name = exp.name        ,
            tier            = exp.tier        ,
            started_at      = utc_now_iso()   ,
            ended_at        = utc_now_iso()   ,
            status          = 'FAILED'        ,
            params          = params          ,
            timings         = []              ,
            observations    = []              ,
            summary         = {}              ,
            cleanup         = {'ledger_entries': 0, 'deleted': 0, 'failed': 0},
            error           = f'{type(exc).__name__}: {exc}\n{traceback.format_exc()}',
        )

    out_path = runner.write_result(result)

    if args.json:
        print(json.dumps(dataclasses.asdict(result), indent=2, default=str))
    else:
        print(render__result_table(result))
        if exp.id in ('E02', 'E04'):
            print()
            print(render__ascii_timeline(result))
        print()
        print(c(f'  run dir: {out_path.parent}', 'dim'))


def cmd_runs_list(args):
    runs_dir = SG_LAB_HOME / 'runs'
    if not runs_dir.exists():
        print('(no runs yet)')
        return
    entries = sorted(runs_dir.iterdir(), reverse=True)[:args.last]
    print(c(f'{"run-id":<32} {"experiment":<32} {"status":<8} {"ended_at"}', 'bold'))
    print('─' * 95)
    for d in entries:
        rp = d / 'result.json'
        if not rp.exists():
            continue
        with rp.open() as f:
            r = json.load(f)
        print(f'{r["run_id"]:<32} {r["experiment_name"]:<32} {r["status"]:<8} {r["ended_at"]}')


def cmd_runs_show(args):
    rp = SG_LAB_HOME / 'runs' / args.run_id / 'result.json'
    if not rp.exists():
        sys.stderr.write(c(f'Run not found: {args.run_id}\n', 'red'))
        sys.exit(2)
    with rp.open() as f:
        d = json.load(f)
    # Reconstruct dataclass for the renderer
    result = Schema__Lab__Run__Result(
        run_id          = d['run_id']          ,
        experiment_id   = d['experiment_id']   ,
        experiment_name = d['experiment_name'] ,
        tier            = d['tier']            ,
        started_at      = d['started_at']      ,
        ended_at        = d['ended_at']        ,
        status          = d['status']          ,
        params          = d['params']          ,
        timings         = [Schema__Lab__Timing__Sample(**t) for t in d['timings']]               ,
        observations    = [Schema__Lab__Resolver__Observation(**o) for o in d['observations']]   ,
        summary         = d['summary']         ,
        cleanup         = d['cleanup']         ,
        error           = d.get('error', ''),
    )
    if args.json:
        print(json.dumps(dataclasses.asdict(result), indent=2, default=str))
    else:
        print(render__result_table(result))
        print()
        print(render__ascii_timeline(result))


def cmd_account_show(args):
    print(c('account', 'bold'))
    print(f'  expected      {os.environ.get("SG_AWS__LAB__EXPECTED_ACCOUNT_ID", "(unset)")}')
    print(f'  region        {os.environ.get("AWS_REGION", "(unset)")}')
    print(f'  lab home      {SG_LAB_HOME.resolve()}')
    print(f'  dnspython     {"yes" if HAS_DNSPYTHON else "NO — install with: pip install dnspython"}')


def main():
    p = argparse.ArgumentParser(prog='sg-lab', description='MVP harness for the sg aws lab brief.')
    sub = p.add_subparsers(dest='command')

    p_list = sub.add_parser('list', help='List available experiments.')
    p_list.set_defaults(func=cmd_list)

    p_run = sub.add_parser('run', help='Run an experiment.')
    p_run.add_argument('experiment_id', help='Experiment id (e.g. E02).')
    p_run.add_argument('--param', action='append', help='Extra key=value param.')
    p_run.add_argument('--name', help='Shortcut for --param name=...')
    p_run.add_argument('--zone', help='Shortcut for --param zone=...')
    p_run.add_argument('--rtype', help='Shortcut for --param rtype=...')
    p_run.add_argument('--repeat', type=int, help='Shortcut for --param repeat=N')
    p_run.add_argument('--json', action='store_true', help='Output JSON instead of rendered table.')
    p_run.set_defaults(func=cmd_run)

    p_runs = sub.add_parser('runs', help='Manage past runs.')
    sub_r  = p_runs.add_subparsers(dest='runs_command')
    p_rl   = sub_r.add_parser('list', help='List past runs.')
    p_rl.add_argument('--last', type=int, default=20)
    p_rl.set_defaults(func=cmd_runs_list)
    p_rs   = sub_r.add_parser('show', help='Show a past run.')
    p_rs.add_argument('run_id')
    p_rs.add_argument('--json', action='store_true')
    p_rs.set_defaults(func=cmd_runs_show)

    p_acc = sub.add_parser('account', help='Show account / environment info.')
    sub_a = p_acc.add_subparsers(dest='account_command')
    p_as  = sub_a.add_parser('show')
    p_as.set_defaults(func=cmd_account_show)

    args = p.parse_args()
    if not hasattr(args, 'func'):
        p.print_help()
        sys.exit(0)
    args.func(args)


if __name__ == '__main__':
    main()
