# ═══════════════════════════════════════════════════════════════════════════════
# Tests — ALB__Perf_Test__Runner
# Drives the 6-phase orchestrator against the in-memory ALB client + fake
# HTTP / wait helpers. No mocks. No patches.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws._shared.enums.Enum__AWS__Phase__Status               import Enum__AWS__Phase__Status
from sgraph_ai_service_playwright__cli.aws.alb.enums.Enum__ALB__Perf_Test__Phase                import Enum__ALB__Perf_Test__Phase
from sgraph_ai_service_playwright__cli.aws.alb.enums.Enum__ALB__Target_Type                     import Enum__ALB__Target_Type
from sgraph_ai_service_playwright__cli.aws.alb.schemas.Schema__ALB__Perf_Test__Probe__Result    import Schema__ALB__Perf_Test__Probe__Result
from sgraph_ai_service_playwright__cli.aws.alb.schemas.Schema__ALB__Perf_Test__Report           import Schema__ALB__Perf_Test__Report
from sgraph_ai_service_playwright__cli.aws.alb.schemas.Schema__ALB__Perf_Test__Request          import Schema__ALB__Perf_Test__Request
from sgraph_ai_service_playwright__cli.aws.alb.service.ALB__Perf_Test__Runner                   import ALB__Perf_Test__Runner

from tests.unit.sgraph_ai_service_playwright__cli.aws.alb.service.ALB__AWS__Client__In_Memory import ALB__AWS__Client__In_Memory


# ── helpers / fakes ──────────────────────────────────────────────────────────

class Fake_HTTP__Probe(Type_Safe):
    results : list = None                                                          # cycle through these per call
    _next   : int  = 0

    def setup(self):
        if self.results is None:
            self.results = []

    def probe(self, url: str) -> Schema__ALB__Perf_Test__Probe__Result:
        self.setup()
        if not self.results:
            result = Schema__ALB__Perf_Test__Probe__Result(
                attempt=self._next + 1, status_code=200, duration_ms=10, body_size=2)
            self._next += 1
            return result
        result = self.results[self._next % len(self.results)]
        self._next += 1
        return result


class Fake_LB__Wait(Type_Safe):
    ok_after_attempts : int = 1
    _calls            : int = 0

    def wait(self, lb_arn, timeout_s):
        self._calls += 1
        if self.ok_after_attempts <= 0:
            return (False, self._calls, 'provisioning')
        return (True, self._calls, 'active')


class Fake_Target__Wait(Type_Safe):
    ok_after_attempts : int = 1
    _calls            : int = 0

    def wait(self, tg_arn, target_id, timeout_s):
        self._calls += 1
        if self.ok_after_attempts <= 0:
            return (False, self._calls, 'unhealthy')
        return (True, self._calls, 'healthy')


class _Fail_Once__Client(ALB__AWS__Client__In_Memory):                              # raises on the first delete_listener call, then behaves normally
    def __init__(self):
        super().__init__()
        self._delete_listener_calls = 0

    def delete_listener(self, listener_arn: str) -> None:
        self._delete_listener_calls += 1
        if self._delete_listener_calls == 1:
            raise RuntimeError(f'simulated teardown failure for {listener_arn}')
        return super().delete_listener(listener_arn)


def _seed_request(**overrides) -> Schema__ALB__Perf_Test__Request:
    req = Schema__ALB__Perf_Test__Request(
        vpc_id          = 'vpc-perf',
        target_ip       = '10.0.1.42',
        target_port     = 8080,
        http_path       = '/info/health',
        expected_status = 200,
        http_probes     = 3,
        name            = overrides.pop('name', 'perf-run-1'),
        keep            = overrides.pop('keep', False),
    )
    for sid in ('subnet-a', 'subnet-b'):
        req.subnet_ids.append(sid)
    for k, v in overrides.items():
        setattr(req, k, v)
    return req


def _make_runner(client, http_probe=None, lb_waiter=None, target_waiter=None):
    return ALB__Perf_Test__Runner(
        alb_client    = client,
        ec2_client    = None,                                                       # in-memory ALB client doesn't need EC2 client for these flows
        http_probe    = http_probe    or Fake_HTTP__Probe(),
        lb_waiter     = lb_waiter     or Fake_LB__Wait(),
        target_waiter = target_waiter or Fake_Target__Wait(),
        sleep_fn      = lambda _s: None,
    )


# ── tests ────────────────────────────────────────────────────────────────────

class Test__ALB__Perf_Test__Runner:

    def test_1__happy_path(self):
        client = ALB__AWS__Client__In_Memory()
        # Seed the target as healthy so register_targets puts it on a known path.
        runner = _make_runner(client)
        req    = _seed_request()
        report = runner.run(req)
        assert report.ok is True
        assert report.target_registered is True
        assert len(report.probes) == 3
        for p in report.probes:
            assert int(p.status_code) == 200
        names = [str(ph.name) for ph in report.phases]
        for expected in (Enum__ALB__Perf_Test__Phase.PROVISION.value,
                          Enum__ALB__Perf_Test__Phase.WAIT_LB_ACTIVE.value,
                          Enum__ALB__Perf_Test__Phase.REGISTER_TARGET.value,
                          Enum__ALB__Perf_Test__Phase.WAIT_HEALTHY.value,
                          Enum__ALB__Perf_Test__Phase.HTTP_PROBE.value,
                          Enum__ALB__Perf_Test__Phase.TEARDOWN.value):
            assert expected in names
        # Verify the LB is destroyed after teardown.
        assert client.describe_load_balancer(report.lb_arn) is None

    def test_2__lb_active_timeout(self):
        client = ALB__AWS__Client__In_Memory()
        runner = _make_runner(client, lb_waiter=Fake_LB__Wait(ok_after_attempts=0))
        report = runner.run(_seed_request())
        assert report.ok is False
        assert 'WAIT_LB_ACTIVE' in report.error
        # TEARDOWN still runs — LB has been destroyed.
        assert client.describe_load_balancer(report.lb_arn) is None
        teardown = [ph for ph in report.phases if str(ph.name) == Enum__ALB__Perf_Test__Phase.TEARDOWN.value]
        assert len(teardown) == 1

    def test_3__target_unhealthy(self):
        client = ALB__AWS__Client__In_Memory()
        runner = _make_runner(client,
                               target_waiter=Fake_Target__Wait(ok_after_attempts=0))
        report = runner.run(_seed_request())
        assert report.ok is False
        assert 'WAIT_HEALTHY' in report.error
        assert client.describe_load_balancer(report.lb_arn) is None

    def test_4__http_status_mismatch(self):
        client = ALB__AWS__Client__In_Memory()
        probe  = Fake_HTTP__Probe(results=[
            Schema__ALB__Perf_Test__Probe__Result(attempt=i+1, status_code=503,
                                                   duration_ms=10, body_size=10)
            for i in range(3)
        ])
        runner = _make_runner(client, http_probe=probe)
        report = runner.run(_seed_request())
        assert report.ok is False
        assert 'HTTP_PROBE' in report.error
        # All 3 probes were captured before raising.
        assert len(report.probes) == 3
        for p in report.probes:
            assert int(p.status_code) == 503
        # TEARDOWN ran.
        assert client.describe_load_balancer(report.lb_arn) is None

    def test_5__http_timeout(self):
        client = ALB__AWS__Client__In_Memory()
        probe  = Fake_HTTP__Probe(results=[
            Schema__ALB__Perf_Test__Probe__Result(attempt=i+1, status_code=0,
                                                   duration_ms=10, body_size=0,
                                                   error='timeout')
            for i in range(3)
        ])
        runner = _make_runner(client, http_probe=probe)
        report = runner.run(_seed_request())
        assert report.ok is False
        assert len(report.probes) == 3
        for p in report.probes:
            assert int(p.status_code) == 0
            assert str(p.error) != ''

    def test_6__keep_flag(self):
        client = ALB__AWS__Client__In_Memory()
        runner = _make_runner(client)
        report = runner.run(_seed_request(keep=True))
        assert report.ok is True
        teardown = [ph for ph in report.phases if str(ph.name) == Enum__ALB__Perf_Test__Phase.TEARDOWN.value]
        assert len(teardown) == 1
        assert teardown[0].status == Enum__AWS__Phase__Status.SKIPPED
        # Stack still exists after run (LB is still there).
        assert client.describe_load_balancer(report.lb_arn) is not None

    def test_7__teardown_failure_recorded(self):
        client = _Fail_Once__Client()
        runner = _make_runner(client)
        report = runner.run(_seed_request())
        # Phase flow succeeded but teardown had an issue.
        assert len(report.rollback_errors) >= 1
        assert any('delete_listener' in str(e) for e in report.rollback_errors)

    def test_8__ip_target_type(self):
        client = ALB__AWS__Client__In_Memory()
        runner = _make_runner(client)
        # Use keep=True so the TG is still present for inspection.
        report = runner.run(_seed_request(keep=True))
        assert report.ok is True
        tgs = list(client.list_target_groups())
        assert len(tgs) == 1
        assert str(tgs[0].target_type) == str(Enum__ALB__Target_Type.IP)

    def test_9__schema_round_trip(self):
        client = ALB__AWS__Client__In_Memory()
        runner = _make_runner(client)
        report = runner.run(_seed_request())
        payload  = report.json()
        restored = Schema__ALB__Perf_Test__Report.from_json(payload)
        assert restored.stack_name == report.stack_name
        assert restored.ok         == report.ok
        assert restored.lb_arn     == report.lb_arn
        assert restored.tg_arn     == report.tg_arn
        assert len(restored.probes) == len(report.probes)
        assert len(restored.phases) == len(report.phases)

    def test_10__auto_generated_name(self):
        client = ALB__AWS__Client__In_Memory()
        runner = _make_runner(client)
        req    = _seed_request(name='')
        report = runner.run(req)
        # f'perf-{secrets.token_hex(4)}' → 'perf-' (5 chars) + 8 hex chars = 13 chars total
        assert report.stack_name.startswith('perf-')
        assert len(report.stack_name) == 13
        hex_part = report.stack_name[5:]
        assert len(hex_part) == 8
        assert all(c in '0123456789abcdef' for c in hex_part)
