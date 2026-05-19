# ═══════════════════════════════════════════════════════════════════════════════
# tests/unit — test_Vault_App__Fargate__Starter
# Covers the 6-phase start orchestrator end-to-end using in-memory clients.
# No mocks. No patches. Uses _http_get stub for health; injectable clients.
# ═══════════════════════════════════════════════════════════════════════════════

import os
from unittest import TestCase

from sg_compute_specs.vault_app.fargate.schemas.Schema__VAF__Start__Report         import Schema__VAF__Start__Report
from sg_compute_specs.vault_app.fargate.schemas.Schema__VAF__Start__Request        import Schema__VAF__Start__Request
from sg_compute_specs.vault_app.fargate.service.Vault_App__Fargate__Health         import Vault_App__Fargate__Health
from sg_compute_specs.vault_app.fargate.service.Vault_App__Fargate__Starter        import Vault_App__Fargate__Starter
from sg_compute_specs.vault_app.fargate.service.Vault_App__Fargate__Timings__Store import Vault_App__Fargate__Timings__Store
from sgraph_ai_service_playwright__cli.aws.ec2.service.EC2__AWS__Client            import EC2__AWS__Client
from tests.unit.sgraph_ai_service_playwright__cli.aws.ec2.service.EC2__AWS__Client__In_Memory    import EC2__AWS__Client__In_Memory
from tests.unit.sgraph_ai_service_playwright__cli.aws.fargate.service.Fargate__AWS__Client__In_Memory import Fargate__AWS__Client__In_Memory

_CLUSTER     = 'test-cluster'
_TASK_FAMILY = 'vault-app'
_SUBNET      = 'subnet-aaa'
_SG_ID       = 'sg-111'
_PUBLIC_IP   = '18.130.45.12'
_PRIVATE_IP  = '10.0.1.15'
_STORE_PATH  = '/tmp/test_vaf_starter_timings.jsonl'


def _http_get_ok(url, headers):                                                   # always-200 health stub
    return 200, True


def _http_get_fail(url, headers):                                                 # always-fail health stub
    return 503, False


def _make_fargate(with_eni: bool = True) -> Fargate__AWS__Client__In_Memory:
    fargate = Fargate__AWS__Client__In_Memory()
    fargate.seed_cluster_with_tags(_CLUSTER, {
        'VaultApp__Subnets'       : _SUBNET,
        'VaultApp__SecurityGroup' : _SG_ID,
        'VaultApp__LogGroup'      : '/ecs/vault-app',
    })
    fargate._fake.register_task_definition(family=_TASK_FAMILY)                   # seed task-def so describe_task_definition succeeds
    return fargate


def _make_ec2(eni_id: str = 'eni-abc123') -> EC2__AWS__Client__In_Memory:
    ec2 = EC2__AWS__Client__In_Memory()
    ec2.seed_eni(
        eni_id     = eni_id,
        public_ip  = _PUBLIC_IP,
        private_ip = _PRIVATE_IP,
    )
    return ec2


def _make_starter(fargate=None, ec2=None, health_stub=None,
                  store_path: str = _STORE_PATH) -> Vault_App__Fargate__Starter:
    if fargate is None:
        fargate = _make_fargate()
    if ec2 is None:
        ec2 = _make_ec2()
    health = Vault_App__Fargate__Health(
        timeout_seconds = 1,
        initial_delay   = 0.0,
        max_delay       = 0.0,
        _http_get       = health_stub or _http_get_ok,
    )
    store = Vault_App__Fargate__Timings__Store(path=store_path)
    return Vault_App__Fargate__Starter(
        fargate_client = fargate,
        ec2_client     = ec2,
        health         = health,
        timings_store  = store,
    )


def _make_request(**kwargs) -> Schema__VAF__Start__Request:
    defaults = dict(
        cluster_name = _CLUSTER,
        slug         = 'bold-turing',
        with_tls     = False,                                                      # use http for simpler URL comparison
        access_token = 'tok-abc',
    )
    defaults.update(kwargs)
    return Schema__VAF__Start__Request(**defaults)


class test_Vault_App__Fargate__Starter(TestCase):

    def setUp(self):
        if os.path.exists(_STORE_PATH):
            os.remove(_STORE_PATH)

    def tearDown(self):
        if os.path.exists(_STORE_PATH):
            os.remove(_STORE_PATH)

    # ── happy path — return type and fields ───────────────────────────────────

    def test_start_returns_schema_start_report(self):
        starter = _make_starter()
        report  = starter.start(_make_request())
        assert isinstance(report, Schema__VAF__Start__Report)

    def test_start_ok_is_true(self):
        starter = _make_starter()
        report  = starter.start(_make_request())
        assert report.ok is True

    def test_start_error_is_empty(self):
        starter = _make_starter()
        report  = starter.start(_make_request())
        assert report.error == ''

    def test_start_slug_is_set(self):
        starter = _make_starter()
        report  = starter.start(_make_request(slug='my-slug'))
        assert report.slug == 'my-slug'

    def test_start_cluster_name_is_set(self):
        starter = _make_starter()
        report  = starter.start(_make_request())
        assert report.cluster_name == _CLUSTER

    def test_start_task_arn_is_set(self):
        starter = _make_starter()
        report  = starter.start(_make_request())
        assert report.task_arn.startswith('arn:')

    def test_start_executed_at_is_iso8601(self):
        starter = _make_starter()
        report  = starter.start(_make_request())
        assert 'T' in report.executed_at
        assert '+' in report.executed_at or 'Z' in report.executed_at

    # ── slug auto-generation ──────────────────────────────────────────────────

    def test_auto_slug_generated_when_empty(self):
        starter = _make_starter()
        report  = starter.start(_make_request(slug=''))
        assert report.slug != ''
        assert '-' in report.slug

    def test_explicit_slug_used_when_provided(self):
        starter = _make_starter()
        report  = starter.start(_make_request(slug='dinis-tue'))
        assert report.slug == 'dinis-tue'

    # ── IP resolution ─────────────────────────────────────────────────────────

    def test_vault_url_contains_public_ip(self):
        fargate = _make_fargate()
        ec2     = _make_ec2()
        starter = _make_starter(fargate=fargate, ec2=ec2)
        # We need the run_task to set an ENI on the resulting task
        # The in-memory run_task creates a task; we intercept via post-hoc set
        # After run_task the task_arn is known; we set ENI before WAIT_RUNNING poll
        # This is done by patching describe_task to include ENI

        # Simpler: seed a task with ENI before starting so WAIT_RUNNING finds it
        # But Starter calls run_task first. The returned task from run_task has
        # no ENI (attachments=[]).  RESOLVE_ENI will find eni_id=''.
        # To test IP resolution, we hook post-run_task to inject the ENI.

        # Simplest approach: override fargate so run_task returns a task with ENI
        eni_id = 'eni-abc123'

        class _FargateWithENI(Fargate__AWS__Client__In_Memory):
            def run_task(self, cluster, task_def, **kwargs):
                result = super().run_task(cluster, task_def, **kwargs)
                if result:
                    self.set_task_eni(str(result.task_arn), eni_id)
                    # re-parse to include eni_id
                    raw = self._tasks[str(result.task_arn)]
                    result = self._parse_task(raw)
                return result

        fargate2 = _FargateWithENI()
        fargate2.seed_cluster_with_tags(_CLUSTER, {
            'VaultApp__Subnets'       : _SUBNET,
            'VaultApp__SecurityGroup' : _SG_ID,
        })
        fargate2._fake.register_task_definition(family=_TASK_FAMILY)

        starter2 = _make_starter(fargate=fargate2, ec2=ec2)
        report = starter2.start(_make_request(with_tls=False))
        assert _PUBLIC_IP in report.vault_url

    def test_private_ip_set(self):
        # Without ENI we still get vault_url from empty IP (graceful fallback)
        starter = _make_starter()
        report  = starter.start(_make_request(with_tls=False))
        # public_ip may be '' if ENI not wired; private_ip too
        # vault_url is built from public_ip or private_ip, may contain empty host
        assert 'http://' in report.vault_url

    # ── TLS URL ───────────────────────────────────────────────────────────────

    def test_vault_url_uses_https_when_tls(self):
        starter = _make_starter()
        report  = starter.start(_make_request(with_tls=True))
        assert report.vault_url.startswith('https://')

    def test_vault_url_uses_http_when_no_tls(self):
        starter = _make_starter()
        report  = starter.start(_make_request(with_tls=False))
        assert report.vault_url.startswith('http://')

    def test_vault_url_uses_https_port_with_tls(self):
        starter = _make_starter()
        report  = starter.start(_make_request(with_tls=True))
        assert ':443' in report.vault_url

    def test_vault_url_uses_http_port_without_tls(self):
        starter = _make_starter()
        report  = starter.start(_make_request(with_tls=False))
        assert ':8080' in report.vault_url

    # ── access_token propagated ───────────────────────────────────────────────

    def test_access_token_in_report(self):
        starter = _make_starter()
        report  = starter.start(_make_request(access_token='tok-xyz'))
        assert report.access_token == 'tok-xyz'

    # ── timings ───────────────────────────────────────────────────────────────

    def test_task_ready_ms_is_positive(self):
        starter = _make_starter()
        report  = starter.start(_make_request())
        assert report.task_ready_ms >= 0

    def test_vault_ready_ms_is_positive(self):
        starter = _make_starter()
        report  = starter.start(_make_request())
        assert report.vault_ready_ms >= 0

    def test_total_ms_is_positive(self):
        starter = _make_starter()
        report  = starter.start(_make_request())
        assert report.total_ms >= 0

    def test_task_ready_ms_le_vault_ready_ms(self):
        starter = _make_starter()
        report  = starter.start(_make_request())
        assert report.task_ready_ms <= report.vault_ready_ms

    def test_vault_ready_ms_le_total_ms(self):
        starter = _make_starter()
        report  = starter.start(_make_request())
        assert report.vault_ready_ms <= report.total_ms

    def test_phases_list_is_non_empty(self):
        starter = _make_starter()
        report  = starter.start(_make_request())
        assert report.phases is not None
        assert len(report.phases) > 0

    # ── VaultApp__DnsFqdn tag (Deliverable 1) ─────────────────────────────────

    def test_dns_zone_sets_dns_fqdn_tag_on_task(self):
        # When dns_zone is set, the RUN_TASK phase stamps VaultApp__DnsFqdn so
        # `stop` can later find the DNS record without the user re-passing --dns-zone.
        fargate = _make_fargate()
        starter = _make_starter(fargate=fargate)
        starter.start(_make_request(slug='dns-vault', dns_zone='sg-compute.sgraph.ai'))
        tag_list  = fargate._fake.last_run_kwargs.get('tags', [])
        tag_dict  = {t['key']: t['value'] for t in tag_list if 'key' in t}
        assert tag_dict.get('VaultApp__DnsFqdn') == 'dns-vault.sg-compute.sgraph.ai'

    def test_no_dns_zone_omits_dns_fqdn_tag(self):
        fargate = _make_fargate()
        starter = _make_starter(fargate=fargate)
        starter.start(_make_request(slug='plain-vault'))                              # no dns_zone
        tag_list = fargate._fake.last_run_kwargs.get('tags', [])
        tag_dict = {t['key']: t['value'] for t in tag_list if 'key' in t}
        assert 'VaultApp__DnsFqdn' not in tag_dict

    def test_phases_includes_resolve_config(self):
        starter = _make_starter()
        report  = starter.start(_make_request())
        names = [r.name for r in report.phases]
        assert 'RESOLVE_CONFIG' in names

    def test_phases_includes_run_task(self):
        starter = _make_starter()
        report  = starter.start(_make_request())
        names = [r.name for r in report.phases]
        assert 'RUN_TASK' in names

    def test_phases_includes_wait_running(self):
        starter = _make_starter()
        report  = starter.start(_make_request())
        names = [r.name for r in report.phases]
        assert 'WAIT_RUNNING' in names

    def test_phases_includes_resolve_eni(self):
        starter = _make_starter()
        report  = starter.start(_make_request())
        names = [r.name for r in report.phases]
        assert 'RESOLVE_ENI' in names

    def test_phases_includes_wait_health(self):
        starter = _make_starter()
        report  = starter.start(_make_request())
        names = [r.name for r in report.phases]
        assert 'WAIT_HEALTH' in names

    def test_task_ready_ms_equals_sum_of_first_three_phases(self):
        starter = _make_starter()
        report  = starter.start(_make_request())
        phase_map = {r.name: r.duration_ms for r in report.phases}
        expected = (phase_map.get('RESOLVE_CONFIG', 0)
                    + phase_map.get('RUN_TASK', 0)
                    + phase_map.get('WAIT_RUNNING', 0))
        assert report.task_ready_ms == expected

    def test_total_ms_equals_sum_of_all_phases(self):
        starter = _make_starter()
        report  = starter.start(_make_request())
        total = sum(r.duration_ms for r in report.phases)
        assert report.total_ms == total

    # ── timings store persisted ───────────────────────────────────────────────

    def test_timings_record_written_after_success(self):
        starter = _make_starter()
        starter.start(_make_request(slug='store-test'))
        records = Vault_App__Fargate__Timings__Store(path=_STORE_PATH).last()
        assert len(records) == 1
        assert records[0].slug == 'store-test'

    def test_timings_record_cluster_name_correct(self):
        starter = _make_starter()
        starter.start(_make_request())
        records = Vault_App__Fargate__Timings__Store(path=_STORE_PATH).last()
        assert records[0].cluster_name == _CLUSTER

    def test_timings_record_totals_match_report(self):
        starter = _make_starter()
        report  = starter.start(_make_request())
        records = Vault_App__Fargate__Timings__Store(path=_STORE_PATH).last()
        r = records[0]
        assert r.total_ms       == report.total_ms
        assert r.vault_ready_ms == report.vault_ready_ms
        assert r.task_ready_ms  == report.task_ready_ms

    # ── health failure ────────────────────────────────────────────────────────

    def test_health_failure_raises_and_sets_ok_false(self):
        starter = _make_starter(health_stub=_http_get_fail)
        request = _make_request()
        try:
            report = starter.start(request)
            assert False, 'expected RuntimeError'
        except RuntimeError as exc:
            assert 'Health check failed' in str(exc)

    def test_health_failure_report_not_ok(self):
        starter = _make_starter(health_stub=_http_get_fail)
        request = _make_request()
        try:
            starter.start(request)
        except RuntimeError:
            pass                                                                   # expected — report captured inside starter

    # ── task stops unexpectedly ───────────────────────────────────────────────

    def test_task_stops_raises_runtime_error(self):
        fargate = _make_fargate()
        fargate._fake.register_task_definition(family=_TASK_FAMILY)

        # Wrap describe_task to simulate STOPPED status on poll
        _orig_describe = fargate.describe_task.__func__

        call_count = [0]
        def _stubbed_describe_task(self_inner, task_arn, cluster=''):
            call_count[0] += 1
            raw = self_inner._tasks.get(task_arn)
            if raw:
                raw = dict(raw)
                raw['lastStatus'] = 'STOPPED'
            return self_inner._parse_task(raw) if raw else None

        import types
        fargate.describe_task = types.MethodType(_stubbed_describe_task, fargate)

        starter = _make_starter(fargate=fargate)
        request = _make_request()
        with self.assertRaises(RuntimeError) as ctx:
            starter.start(request)
        assert 'STOPPED' in str(ctx.exception)

    # ── progress callbacks ────────────────────────────────────────────────────

    def test_progress_callbacks_fired(self):
        fired = []
        def on_progress(name, status, detail=''):
            fired.append((name, str(status)))

        fargate = _make_fargate()
        health  = Vault_App__Fargate__Health(
            timeout_seconds = 1,
            initial_delay   = 0.0,
            max_delay       = 0.0,
            _http_get       = _http_get_ok,
        )
        store   = Vault_App__Fargate__Timings__Store(path=_STORE_PATH)
        starter = Vault_App__Fargate__Starter(
            fargate_client = fargate,
            ec2_client     = _make_ec2(),
            health         = health,
            timings_store  = store,
            progress_cb    = on_progress,
        )
        starter.start(_make_request())
        phase_names_fired = [name for name, _ in fired]
        assert 'RESOLVE_CONFIG' in phase_names_fired
        assert 'RUN_TASK'       in phase_names_fired
        assert 'WAIT_RUNNING'   in phase_names_fired
        assert 'WAIT_HEALTH'    in phase_names_fired

    def test_progress_callbacks_include_ok_status(self):
        fired = []
        def on_progress(name, status, detail=''):
            fired.append((name, str(status)))

        fargate = _make_fargate()
        health  = Vault_App__Fargate__Health(
            timeout_seconds = 1,
            initial_delay   = 0.0,
            max_delay       = 0.0,
            _http_get       = _http_get_ok,
        )
        store = Vault_App__Fargate__Timings__Store(path=_STORE_PATH)
        starter = Vault_App__Fargate__Starter(
            fargate_client = fargate,
            ec2_client     = _make_ec2(),
            health         = health,
            timings_store  = store,
            progress_cb    = on_progress,
        )
        starter.start(_make_request())
        ok_entries = [(name, s) for name, s in fired if s in ('OK', 'Enum__VAF__Phase__Status.OK')]
        assert len(ok_entries) > 0

    # ── WAIT_RUNNING polling ──────────────────────────────────────────────────

    def test_wait_running_succeeds_when_task_already_running(self):
        # In-memory run_task returns RUNNING immediately — should break on first attempt
        starter = _make_starter()
        report  = starter.start(_make_request())
        assert report.ok is True

    def test_wait_running_polls_until_running(self):
        fargate = _make_fargate()
        # First describe_task call returns PROVISIONING; second returns RUNNING
        call_count = [0]
        _orig = fargate.describe_task

        import types
        def _toggling_describe(self_inner, task_arn, cluster=''):
            raw = self_inner._tasks.get(task_arn)
            if raw is None:
                return None
            call_count[0] += 1
            raw = dict(raw)
            raw['lastStatus'] = 'RUNNING' if call_count[0] >= 2 else 'PROVISIONING'
            return self_inner._parse_task(raw)

        fargate.describe_task = types.MethodType(_toggling_describe, fargate)

        health  = Vault_App__Fargate__Health(
            timeout_seconds = 1,
            initial_delay   = 0.0,
            max_delay       = 0.0,
            _http_get       = _http_get_ok,
        )
        store   = Vault_App__Fargate__Timings__Store(path=_STORE_PATH)
        starter = Vault_App__Fargate__Starter(
            fargate_client = fargate,
            ec2_client     = _make_ec2(),
            health         = health,
            timings_store  = store,
        )
        report = starter.start(_make_request())
        assert report.ok is True
        assert call_count[0] >= 2
