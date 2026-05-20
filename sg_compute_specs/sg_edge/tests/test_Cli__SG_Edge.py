# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge: tests for the sg edge CLI
# Tests are grouped by sub-app and cover:
#   — registration: sg edge and sg ed are present; no existing command is broken
#   — proxy sub-app: pure-asset commands (no AWS)
#   — bench sub-app: all Slice 6 stubs return 0 + expected message
#   — waker sub-app: logs stub returns 0
#   — umbrella stubs: boot / reconcile / drain return 0 + Slice 5 message
#   — dns sub-app: all four commands with SG_Edge__DNS__Helper injected via
#     module-level _dns_factory (Route53__AWS__Client__In_Memory, no mocks)
#   — status command: no-parent error + with injected reconciler
#   — idle-check command: increment/reset paths with injected reconciler
# ═══════════════════════════════════════════════════════════════════════════════

import json
from unittest import TestCase, skipUnless

try:
    from typer.testing import CliRunner                                              # noqa: F401 — availability probe
    _HAS_TYPER = True
except Exception:
    _HAS_TYPER = False

if _HAS_TYPER:
    from sg_compute_specs.sg_edge.cli.Cli__SG_Edge        import app as edge_app
    from sg_compute_specs.sg_edge.cli.Cli__SG_Edge__Proxy  import app as proxy_app
    from sg_compute_specs.sg_edge.cli.Cli__SG_Edge__Bench  import app as bench_app
    from sg_compute_specs.sg_edge.cli.Cli__SG_Edge__Waker  import app as waker_app
    from sg_compute_specs.sg_edge.cli.Cli__SG_Edge__Dns    import app as dns_app
    import sg_compute_specs.sg_edge.cli.Cli__SG_Edge__Dns  as dns_mod
    import sg_compute_specs.sg_edge.cli.Cli__SG_Edge       as edge_mod

PARENT = 'test.sg-labs.app'


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _make_dns_helper():
    from tests.unit.sgraph_ai_service_playwright__cli.aws.dns.service.Route53__AWS__Client__In_Memory import Route53__AWS__Client__In_Memory
    from sg_compute_specs.sg_edge.service.SG_Edge__DNS__Helper import SG_Edge__DNS__Helper
    r53 = Route53__AWS__Client__In_Memory()
    r53.seed_zone(PARENT)
    return SG_Edge__DNS__Helper(route53=r53)


def _make_reconciler(helper, parent=PARENT):
    from sg_compute_specs.sg_edge.service.SG_Edge__Fleet__Reconciler import SG_Edge__Fleet__Reconciler
    return SG_Edge__Fleet__Reconciler(dns=helper, parent=parent)


# ═══════════════════════════════════════════════════════════════════════════════
# Registration
# ═══════════════════════════════════════════════════════════════════════════════

@skipUnless(_HAS_TYPER, 'typer not installed (Python <3.12 in this env)')
class test_Cli__SG_Edge__Registration(TestCase):

    def test_sg_edge_is_registered_in_top_level_cli(self):
        from sg_compute.cli.Cli__SG import app as sg_app
        names = {t.name for t in sg_app.registered_groups}
        assert 'edge'       in names
        assert 'ed'         in names
        assert 'edge_bench' in names

    def test_existing_commands_unperturbed(self):
        from sg_compute.cli.Cli__SG import app as sg_app
        names = {t.name for t in sg_app.registered_groups}
        for expected in ('aws', 'docker', 'elastic', 'vault-publish', 'vault-app', 'playwright'):
            assert expected in names, f'existing command {expected!r} missing after edge registration'

    def test_edge_app_has_expected_commands(self):
        runner = CliRunner()
        result = runner.invoke(edge_app, ['--help'])
        assert result.exit_code == 0
        for cmd in ('status', 'idle-check', 'boot', 'reconcile', 'drain', 'dns', 'proxy', 'bench', 'waker'):
            assert cmd in result.output, f'command {cmd!r} missing from sg edge --help'


# ═══════════════════════════════════════════════════════════════════════════════
# Proxy sub-app (pure-asset, no AWS)
# ═══════════════════════════════════════════════════════════════════════════════

@skipUnless(_HAS_TYPER, 'typer not installed (Python <3.12 in this env)')
class test_Cli__SG_Edge__Proxy(TestCase):

    def setUp(self):
        self.runner = CliRunner()

    def test_nginx_conf__exits_0(self):
        result = self.runner.invoke(proxy_app, ['nginx-conf'], catch_exceptions=False)
        assert result.exit_code == 0

    def test_nginx_conf__contains_both_ports(self):
        result = self.runner.invoke(proxy_app, ['nginx-conf'], catch_exceptions=False)
        assert 'listen      80 default_server;' in result.output
        assert 'listen      8089;'              in result.output

    def test_user_data__exits_0(self):
        result = self.runner.invoke(proxy_app, ['user-data'], catch_exceptions=False)
        assert result.exit_code == 0

    def test_user_data__contains_shebang(self):
        result = self.runner.invoke(proxy_app, ['user-data'], catch_exceptions=False)
        assert '#!/bin/bash' in result.output

    def test_user_data__version_flag(self):
        result = self.runner.invoke(proxy_app, ['user-data', '--version', '2.3.4'], catch_exceptions=False)
        assert result.exit_code == 0
        assert 'EDGE_VERSION="2.3.4"' in result.output

    def test_cf_function__exits_0(self):
        result = self.runner.invoke(proxy_app, ['cf-function'], catch_exceptions=False)
        assert result.exit_code == 0

    def test_cf_function__contains_handler(self):
        result = self.runner.invoke(proxy_app, ['cf-function'], catch_exceptions=False)
        assert 'function handler(event)' in result.output
        assert 'x-sg-slug'               in result.output


# ═══════════════════════════════════════════════════════════════════════════════
# Bench sub-app stubs (all Slice 6)
# ═══════════════════════════════════════════════════════════════════════════════

@skipUnless(_HAS_TYPER, 'typer not installed (Python <3.12 in this env)')
class test_Cli__SG_Edge__Bench(TestCase):

    def setUp(self):
        self.runner = CliRunner()

    def test_list__shows_catalog(self):
        result = self.runner.invoke(bench_app, ['list'], catch_exceptions=False)
        assert result.exit_code == 0
        assert 'F-01' in result.output
        assert 'P-03' in result.output

    def test_scenario_local__passes(self):
        result = self.runner.invoke(bench_app, ['scenario', 'F-01', '--repeat', '2'], catch_exceptions=False)
        assert result.exit_code == 0
        assert 'PASS' in result.output
        assert 'F-01' in result.output

    def test_scenario_aws_bench__skips(self):
        result = self.runner.invoke(bench_app, ['scenario', 'P-01', '--repeat', '2'], catch_exceptions=False)
        assert result.exit_code == 0                                                 # skipped is not a failure
        assert 'SKIP' in result.output

    def test_scenario_unknown__exits_1(self):
        result = self.runner.invoke(bench_app, ['scenario', 'ZZ-99'])
        assert result.exit_code == 1

    def test_scenario_json(self):
        result = self.runner.invoke(bench_app, ['scenario', 'P-12', '--repeat', '2', '--json'], catch_exceptions=False)
        data = json.loads(result.output[result.output.index('{'):])                  # JSON is printed after the rendered table
        assert data['id']     == 'P-12'
        assert data['passed'] is True

    def test_primitives_exits_0(self):
        result = self.runner.invoke(bench_app, ['primitives', '--repeat', '2'], catch_exceptions=False)
        assert result.exit_code == 0
        assert 'ran passed' in result.output

    def test_flows_exits_0(self):
        result = self.runner.invoke(bench_app, ['flows', '--repeat', '2'], catch_exceptions=False)
        assert result.exit_code == 0

    def test_failures_exits_0(self):
        result = self.runner.invoke(bench_app, ['failures', '--repeat', '2'], catch_exceptions=False)
        assert result.exit_code == 0

    def test_full_exits_0(self):
        result = self.runner.invoke(bench_app, ['full', '--repeat', '1'], catch_exceptions=False)
        assert result.exit_code == 0
        assert 'PASS' in result.output

    def test_bad_target__exits_2(self):
        result = self.runner.invoke(bench_app, ['scenario', 'F-01', '--target', 'bogus'])
        assert result.exit_code != 0


# ═══════════════════════════════════════════════════════════════════════════════
# Waker sub-app stubs
# ═══════════════════════════════════════════════════════════════════════════════

@skipUnless(_HAS_TYPER, 'typer not installed (Python <3.12 in this env)')
class test_Cli__SG_Edge__Waker(TestCase):

    def setUp(self):
        self.runner = CliRunner()

    def test_logs_exits_0(self):
        result = self.runner.invoke(waker_app, ['logs'], catch_exceptions=False)
        assert result.exit_code == 0
        assert 'Slice 5' in result.output

    def test_invoke_health__exits_0(self):                                       # /health is fully offline (no DNS)
        result = self.runner.invoke(waker_app, ['invoke', 'health'], catch_exceptions=False)
        assert result.exit_code == 0
        assert '200'           in result.output
        assert 'sg-edge-waker' in result.output

    def test_invoke_unknown_route__exits_1(self):
        result = self.runner.invoke(waker_app, ['invoke', 'bogus'])
        assert result.exit_code == 1


# ═══════════════════════════════════════════════════════════════════════════════
# Umbrella stubs (boot / reconcile / drain = Slice 5)
# ═══════════════════════════════════════════════════════════════════════════════

@skipUnless(_HAS_TYPER, 'typer not installed (Python <3.12 in this env)')
class test_Cli__SG_Edge__Stubs(TestCase):

    def setUp(self):
        self.runner = CliRunner()

    def test_boot_exits_0(self):
        result = self.runner.invoke(edge_app, ['boot'], catch_exceptions=False)
        assert result.exit_code == 0
        assert 'Slice 5' in result.output

    def test_reconcile_exits_0(self):
        result = self.runner.invoke(edge_app, ['reconcile'], catch_exceptions=False)
        assert result.exit_code == 0
        assert 'Slice 5' in result.output

    def test_drain_exits_0(self):
        result = self.runner.invoke(edge_app, ['drain'], catch_exceptions=False)
        assert result.exit_code == 0
        assert 'Slice 5' in result.output


# ═══════════════════════════════════════════════════════════════════════════════
# DNS sub-app — injected in-memory DNS helper
# ═══════════════════════════════════════════════════════════════════════════════

@skipUnless(_HAS_TYPER, 'typer not installed (Python <3.12 in this env)')
class test_Cli__SG_Edge__Dns(TestCase):

    def setUp(self):
        self.helper = _make_dns_helper()
        dns_mod._dns_factory = lambda: self.helper
        self.runner = CliRunner()

    def tearDown(self):
        dns_mod._dns_factory = None

    def test_proxies__empty(self):
        result = self.runner.invoke(dns_app, ['proxies', '--parent', PARENT], catch_exceptions=False)
        assert result.exit_code == 0
        assert 'none' in result.output.lower()

    def test_proxies__with_ip(self):
        self.helper.add_proxy_ip(PARENT, '1.2.3.4')
        result = self.runner.invoke(dns_app, ['proxies', '--parent', PARENT], catch_exceptions=False)
        assert result.exit_code == 0
        assert '1.2.3.4' in result.output

    def test_proxies__json_output(self):
        self.helper.add_proxy_ip(PARENT, '5.6.7.8')
        result = self.runner.invoke(dns_app, ['proxies', '--parent', PARENT, '--json'], catch_exceptions=False)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['parent'] == PARENT
        assert '5.6.7.8' in data['ips']

    def test_parent_defaults_to_edge_sg_labs_app(self):
        from sg_compute_specs.sg_edge.cli.Cli__SG_Edge__Dns import _parent_from
        assert _parent_from('') == 'edge.sg-labs.app'                                 # hard-coded create/destroy-at-will zone
        assert _parent_from('other.example.com') == 'other.example.com'              # explicit --parent still wins

    def test_state__zeroed_when_absent(self):
        result = self.runner.invoke(dns_app, ['state', '--parent', PARENT], catch_exceptions=False)
        assert result.exit_code == 0
        assert 'zero_streak' in result.output

    def test_state__json(self):
        from sg_compute_specs.sg_edge.schemas.Schema__SG_Edge__State__Record import Schema__SG_Edge__State__Record
        self.helper.write_state(PARENT, Schema__SG_Edge__State__Record(zero_streak=3, updated=1000))
        result = self.runner.invoke(dns_app, ['state', '--parent', PARENT, '--json'], catch_exceptions=False)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['zero_streak'] == 3
        assert data['updated']     == 1000

    def test_slugs__empty(self):
        result = self.runner.invoke(dns_app, ['slugs', '--parent', PARENT], catch_exceptions=False)
        assert result.exit_code == 0
        assert 'none' in result.output.lower()

    def test_slugs__with_routing_record(self):
        from tests.unit.sgraph_ai_service_playwright__cli.aws.dns.service.Route53__AWS__Client__In_Memory import Route53__AWS__Client__In_Memory
        from sg_compute_specs.sg_edge.service.SG_Edge__DNS__Helper import SG_Edge__DNS__Helper
        r53 = Route53__AWS__Client__In_Memory()
        r53.seed_zone(PARENT)
        r53.seed_record(PARENT, f'_sg.alice.{PARENT}', 'TXT',
                        ['"v=1;ip=10.0.1.5;port=8080;type=ec2;launched=1000"'])
        self.helper = SG_Edge__DNS__Helper(route53=r53)
        dns_mod._dns_factory = lambda: self.helper
        result = self.runner.invoke(dns_app, ['slugs', '--parent', PARENT], catch_exceptions=False)
        assert result.exit_code == 0
        assert 'alice' in result.output

    def test_slugs__json(self):
        result = self.runner.invoke(dns_app, ['slugs', '--parent', PARENT, '--json'], catch_exceptions=False)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert 'slugs' in data

    def test_routing__absent_exits_1(self):
        result = self.runner.invoke(dns_app, ['routing', 'ghost', '--parent', PARENT])
        assert result.exit_code == 1

    def test_routing__present(self):
        from tests.unit.sgraph_ai_service_playwright__cli.aws.dns.service.Route53__AWS__Client__In_Memory import Route53__AWS__Client__In_Memory
        from sg_compute_specs.sg_edge.service.SG_Edge__DNS__Helper import SG_Edge__DNS__Helper
        r53 = Route53__AWS__Client__In_Memory()
        r53.seed_zone(PARENT)
        r53.seed_record(PARENT, f'_sg.bob.{PARENT}', 'TXT',
                        ['"v=1;ip=10.0.2.3;port=8080;type=ec2;launched=1700000000"'])
        self.helper = SG_Edge__DNS__Helper(route53=r53)
        dns_mod._dns_factory = lambda: self.helper
        result = self.runner.invoke(dns_app, ['routing', 'bob', '--parent', PARENT], catch_exceptions=False)
        assert result.exit_code == 0
        assert '10.0.2.3' in result.output

    def test_routing__json(self):
        from tests.unit.sgraph_ai_service_playwright__cli.aws.dns.service.Route53__AWS__Client__In_Memory import Route53__AWS__Client__In_Memory
        from sg_compute_specs.sg_edge.service.SG_Edge__DNS__Helper import SG_Edge__DNS__Helper
        r53 = Route53__AWS__Client__In_Memory()
        r53.seed_zone(PARENT)
        r53.seed_record(PARENT, f'_sg.sara.{PARENT}', 'TXT',
                        ['"v=1;ip=192.168.1.1;port=8080;type=ec2;launched=1700000001"'])
        helper = SG_Edge__DNS__Helper(route53=r53)
        dns_mod._dns_factory = lambda: helper
        result = self.runner.invoke(dns_app, ['routing', 'sara', '--parent', PARENT, '--json'],
                                    catch_exceptions=False)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['ip'] == '192.168.1.1'


# ═══════════════════════════════════════════════════════════════════════════════
# Status command — injected reconciler
# ═══════════════════════════════════════════════════════════════════════════════

@skipUnless(_HAS_TYPER, 'typer not installed (Python <3.12 in this env)')
class test_Cli__SG_Edge__Status(TestCase):

    def setUp(self):
        self.helper = _make_dns_helper()
        self.runner = CliRunner()

    def tearDown(self):
        edge_mod._reconciler_factory = None

    def test_status__empty_fleet(self):
        edge_mod._reconciler_factory = lambda p: _make_reconciler(self.helper, p)
        result = self.runner.invoke(edge_app, ['status', '--parent', PARENT], catch_exceptions=False)
        assert result.exit_code == 0
        assert 'Proxy count' in result.output
        assert '0' in result.output

    def test_status__with_proxy(self):
        self.helper.add_proxy_ip(PARENT, '10.0.0.1')
        edge_mod._reconciler_factory = lambda p: _make_reconciler(self.helper, p)
        result = self.runner.invoke(edge_app, ['status', '--parent', PARENT], catch_exceptions=False)
        assert result.exit_code == 0
        assert '10.0.0.1' in result.output

    def test_status__json(self):
        self.helper.add_proxy_ip(PARENT, '10.0.0.2')
        edge_mod._reconciler_factory = lambda p: _make_reconciler(self.helper, p)
        result = self.runner.invoke(edge_app, ['status', '--parent', PARENT, '--json'],
                                    catch_exceptions=False)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['proxy_count']  == 1
        assert '10.0.0.2'           in data['proxy_ips']
        assert data['active_slugs'] == []
        assert data['zero_streak']  == 0
        assert 'desired'            in data


# ═══════════════════════════════════════════════════════════════════════════════
# Idle-check command — injected reconciler
# ═══════════════════════════════════════════════════════════════════════════════

@skipUnless(_HAS_TYPER, 'typer not installed (Python <3.12 in this env)')
class test_Cli__SG_Edge__IdleCheck(TestCase):

    def setUp(self):
        self.helper = _make_dns_helper()
        self.runner = CliRunner()

    def tearDown(self):
        edge_mod._reconciler_factory = None

    def test_idle_check__increment_when_no_slugs(self):
        edge_mod._reconciler_factory = lambda p: _make_reconciler(self.helper, p)
        result = self.runner.invoke(edge_app, ['idle-check', '--parent', PARENT], catch_exceptions=False)
        assert result.exit_code == 0
        assert 'increment' in result.output

    def test_idle_check__reset_when_slugs_active(self):
        from tests.unit.sgraph_ai_service_playwright__cli.aws.dns.service.Route53__AWS__Client__In_Memory import Route53__AWS__Client__In_Memory
        from sg_compute_specs.sg_edge.service.SG_Edge__DNS__Helper import SG_Edge__DNS__Helper
        r53 = Route53__AWS__Client__In_Memory()
        r53.seed_zone(PARENT)
        r53.seed_record(PARENT, f'_sg.cv.{PARENT}', 'TXT',
                        ['"v=1;ip=10.0.1.5;port=8080;type=ec2;launched=1000"'])
        helper = SG_Edge__DNS__Helper(route53=r53)
        edge_mod._reconciler_factory = lambda p: _make_reconciler(helper, p)
        result = self.runner.invoke(edge_app, ['idle-check', '--parent', PARENT], catch_exceptions=False)
        assert result.exit_code == 0
        assert 'reset' in result.output

    def test_idle_check__json_output(self):
        edge_mod._reconciler_factory = lambda p: _make_reconciler(self.helper, p)
        result = self.runner.invoke(edge_app, ['idle-check', '--parent', PARENT, '--json'],
                                    catch_exceptions=False)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert 'action'      in data
        assert 'zero_streak' in data
        assert 'active'      in data
