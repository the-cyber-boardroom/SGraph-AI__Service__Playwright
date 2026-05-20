# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge bench: Edge_Bench__Scenarios
# The doc-05 scenario catalog, with runnable LOCAL implementations over the
# `sg edge local` stack. This is a registry module (rule #21 exception): module
# constants + functions, not a schema.
#
# Each registry entry is {descriptor, make, thresholds}:
#   • descriptor — Schema__Edge_Bench__Scenario (id / name / tier / target / doc)
#   • make(state_dir) -> callable()  — builds the per-run measure fn (None for
#     aws-bench-only scenarios). Warm scenarios set state up once in make(); cold
#     scenarios reset inside the returned run fn. Each run returns {name: ms}.
#   • thresholds — {metric_name: (target_ms, hard_fail_ms)} for the LOCAL target.
#
# LOCAL thresholds are code-path budgets (generous, to catch gross regressions
# without CI flakiness) — NOT the brief's AWS acceptance thresholds, which apply to
# the aws-bench target (its execution backend is Slice-5/6 live-AWS, not built).
# Functional correctness is asserted inside each run fn (fail-fast, no retries —
# doc-05 decision #3); a wrong outcome raises and fails the scenario regardless of
# timing.
# ═══════════════════════════════════════════════════════════════════════════════

from time import perf_counter

from sg_compute_specs.sg_edge.bench.enums.Enum__Edge_Bench__Tier            import Enum__Edge_Bench__Tier
from sg_compute_specs.sg_edge.bench.enums.Enum__Edge_Bench__Target          import Enum__Edge_Bench__Target
from sg_compute_specs.sg_edge.bench.schemas.Schema__Edge_Bench__Scenario    import Schema__Edge_Bench__Scenario
from sg_compute_specs.sg_edge.local.Local__Edge__Stack                      import Local__Edge__Stack
from sg_compute_specs.sg_edge.local.enums.Enum__Local__Edge__Response_Kind  import Enum__Local__Edge__Response_Kind

PRIMITIVE = Enum__Edge_Bench__Tier.PRIMITIVE
FLOW      = Enum__Edge_Bench__Tier.FLOW
FAILURE   = Enum__Edge_Bench__Tier.FAILURE
LOCAL     = Enum__Edge_Bench__Target.LOCAL
AWS_BENCH = Enum__Edge_Bench__Target.AWS_BENCH

WELCOME        = Enum__Local__Edge__Response_Kind.WELCOME
DORMANT        = Enum__Local__Edge__Response_Kind.DORMANT
NOT_RECOGNISED = Enum__Local__Edge__Response_Kind.NOT_RECOGNISED


def _ms(t0: float, t1: float) -> int:
    return max(0, int((t1 - t0) * 1000))


# ── LOCAL scenario builders ────────────────────────────────────────────────────

def _make_p03(state_dir):                                                            # P-03 — DNS write + read-back (warm edge)
    stack = Local__Edge__Stack(state_dir=state_dir); stack.setup()
    n = {'i': 0}
    def run():
        n['i'] += 1
        slug = f'p03-{n["i"]}'
        t0 = perf_counter(); stack.register(slug);          t1 = perf_counter()
        view = stack.slug_view(slug);                        t2 = perf_counter()
        if not (view.has_a and view.has_txt):
            raise AssertionError('P-03: register did not write both A and TXT')
        return {'dns_write': _ms(t0, t1), 'dns_read': _ms(t1, t2)}
    return run


def _make_p07(state_dir):                                                            # P-07 — warm proxy response (welcome hot path)
    stack = Local__Edge__Stack(state_dir=state_dir); stack.setup(); stack.register('p07')
    def run():
        t0 = perf_counter(); resp = stack.request('p07'); t1 = perf_counter()
        if resp.kind != WELCOME:
            raise AssertionError(f'P-07: expected welcome, got {resp.kind}')
        return {'response': _ms(t0, t1)}
    return run


def _make_p12(state_dir):                                                            # P-12 — slug-not-found serve time
    stack = Local__Edge__Stack(state_dir=state_dir); stack.setup()
    def run():
        t0 = perf_counter(); resp = stack.request('p12-unknown'); t1 = perf_counter()
        if resp.kind != NOT_RECOGNISED:
            raise AssertionError(f'P-12: expected not_recognised, got {resp.kind}')
        return {'response': _ms(t0, t1)}
    return run


def _make_f01(state_dir):                                                            # F-01 — cold-cold boot end-to-end (cold each run)
    stack = Local__Edge__Stack(state_dir=state_dir)
    def run():
        stack.teardown()
        t0 = perf_counter(); stack.setup();          t1 = perf_counter()
        stack.register('f01');                       t2 = perf_counter()
        resp = stack.request('f01');                 t3 = perf_counter()
        if resp.kind != WELCOME:
            raise AssertionError(f'F-01: expected welcome, got {resp.kind}')
        return {'setup': _ms(t0, t1), 'register': _ms(t1, t2),
                'request': _ms(t2, t3), 'total': _ms(t0, t3)}
    return run


def _make_f06(state_dir):                                                            # F-06 — full cycle: cold → warm → unregister → 404
    stack = Local__Edge__Stack(state_dir=state_dir)
    def run():
        stack.teardown(); stack.setup()
        t0 = perf_counter()
        stack.register('f06')
        r1 = stack.request('f06')
        stack.unregister('f06')
        r2 = stack.request('f06')
        t1 = perf_counter()
        if r1.kind != WELCOME or r2.kind != NOT_RECOGNISED:
            raise AssertionError(f'F-06: expected welcome→not_recognised, got {r1.kind}→{r2.kind}')
        return {'cycle_total': _ms(t0, t1)}
    return run


def _make_f08(state_dir):                                                            # F-08 — registered-but-dormant serve (loading page)
    stack = Local__Edge__Stack(state_dir=state_dir); stack.setup(); stack.register('f08', with_backend=False)
    def run():
        t0 = perf_counter(); resp = stack.request('f08'); t1 = perf_counter()
        if resp.kind != DORMANT:
            raise AssertionError(f'F-08: expected dormant, got {resp.kind}')
        return {'response': _ms(t0, t1)}
    return run


def _make_x07(state_dir):                                                            # X-07 — A record missing → 404 (correctness under unknown slug)
    stack = Local__Edge__Stack(state_dir=state_dir); stack.setup()
    def run():
        t0 = perf_counter(); resp = stack.request('x07-never-registered'); t1 = perf_counter()
        if resp.kind != NOT_RECOGNISED:
            raise AssertionError(f'X-07: expected not_recognised, got {resp.kind}')
        return {'response': _ms(t0, t1)}
    return run


def _make_x12(state_dir):                                                            # X-12 — enumeration: 50 unknown slugs, all 404 (cost of the reject path)
    stack = Local__Edge__Stack(state_dir=state_dir); stack.setup()
    n = {'i': 0}
    def run():
        n['i'] += 1
        t0 = perf_counter()
        for j in range(50):
            resp = stack.request(f'x12-{n["i"]}-{j}')
            if resp.kind != NOT_RECOGNISED:
                raise AssertionError(f'X-12: expected not_recognised for probe {j}, got {resp.kind}')
        t1 = perf_counter()
        return {'enumeration_50': _ms(t0, t1)}
    return run


# ── registry ────────────────────────────────────────────────────────────────────

def _scenario(id, name, tier, target, doc):
    return Schema__Edge_Bench__Scenario(id=id, name=name, tier=tier, target=target, doc=doc)


SCENARIOS = {
    # ── local-runnable (the `sg edge local` stack exercises these in-process) ──
    'P-03': {'descriptor': _scenario('P-03', 'route53_record_write', PRIMITIVE, LOCAL,
                                     'write a slug A+TXT and read the routing back (local DNS file).'),
             'make': _make_p03, 'thresholds': {'dns_write': (100, 2000), 'dns_read': (100, 2000)}},
    'P-07': {'descriptor': _scenario('P-07', 'proxy_static_response', PRIMITIVE, LOCAL,
                                     'warm proxy serves the welcome page (the hot-path response).'),
             'make': _make_p07, 'thresholds': {'response': (100, 2000)}},
    'P-12': {'descriptor': _scenario('P-12', 'slug_not_found_serve_time', PRIMITIVE, LOCAL,
                                     'proxy serves the "slug not recognised" 404.'),
             'make': _make_p12, 'thresholds': {'response': (100, 2000)}},
    'F-01': {'descriptor': _scenario('F-01', 'edge_cold_cold_boot', FLOW, LOCAL,
                                     'cold edge: setup → register → first welcome request, end-to-end.'),
             'make': _make_f01, 'thresholds': {'setup': (200, 3000), 'register': (100, 2000),
                                               'request': (100, 2000), 'total': (500, 5000)}},
    'F-06': {'descriptor': _scenario('F-06', 'cold_to_warm_to_cold', FLOW, LOCAL,
                                     'full cycle: setup → register → welcome → unregister → 404.'),
             'make': _make_f06, 'thresholds': {'cycle_total': (500, 5000)}},
    'F-08': {'descriptor': _scenario('F-08', 'registered_but_dormant', FLOW, LOCAL,
                                     'registered slug with no backend serves the dormant/loading page.'),
             'make': _make_f08, 'thresholds': {'response': (100, 2000)}},
    'X-07': {'descriptor': _scenario('X-07', 'a_record_missing', FAILURE, LOCAL,
                                     'unknown slug (no A record) is rejected with a 404.'),
             'make': _make_x07, 'thresholds': {'response': (100, 2000)}},
    'X-12': {'descriptor': _scenario('X-12', 'enumeration_attempt', FAILURE, LOCAL,
                                     '50 random unknown slugs all serve 404 (reject-path cost).'),
             'make': _make_x12, 'thresholds': {'enumeration_50': (1000, 10000)}},

    # ── aws-bench-only (genuinely AWS-timing; no local analog; backend not built) ──
    'P-01': {'descriptor': _scenario('P-01', 'ec2_boot_time',          PRIMITIVE, AWS_BENCH,
                                     'RunInstances → TCP-accepting (real EC2 boot variance).'), 'make': None, 'thresholds': {}},
    'P-05': {'descriptor': _scenario('P-05', 'cf_origin_dns_refresh',  PRIMITIVE, AWS_BENCH,
                                     'CloudFront sees a changed origin A record (POP cache).'),   'make': None, 'thresholds': {}},
    'P-06': {'descriptor': _scenario('P-06', 'cf_origin_failover',     PRIMITIVE, AWS_BENCH,
                                     'CloudFront primary-unreachable → secondary serving.'),       'make': None, 'thresholds': {}},
    'P-10': {'descriptor': _scenario('P-10', 'lambda_function_url_cold', PRIMITIVE, AWS_BENCH,
                                     'Edge Waker Function URL cold start.'),                        'make': None, 'thresholds': {}},
    'P-11': {'descriptor': _scenario('P-11', 'ec2_terminate_time',     PRIMITIVE, AWS_BENCH,
                                     'TerminateInstances → instance gone.'),                        'make': None, 'thresholds': {}},
    'X-04': {'descriptor': _scenario('X-04', 'edge_waker_killed_mid_boot', FAILURE, AWS_BENCH,
                                     'next CF failover finishes a partially-booted fleet.'),        'make': None, 'thresholds': {}},
    'X-05': {'descriptor': _scenario('X-05', 'concurrent_cold_cold',   FAILURE, AWS_BENCH,
                                     '5 simultaneous failovers launch <=3 proxies, no errors.'),    'make': None, 'thresholds': {}},
    'X-10': {'descriptor': _scenario('X-10', 'cf_origin_health_unreachable', FAILURE, AWS_BENCH,
                                     'CF fails over to secondary through edge cache layers.'),      'make': None, 'thresholds': {}},
}


def scenario_ids() -> list:
    return list(SCENARIOS.keys())


def descriptors(target=None, tier=None) -> list:                                     # filtered descriptors
    out = []
    for entry in SCENARIOS.values():
        d = entry['descriptor']
        if target is not None and d.target != target:
            continue
        if tier is not None and d.tier != tier:
            continue
        out.append(d)
    return out
