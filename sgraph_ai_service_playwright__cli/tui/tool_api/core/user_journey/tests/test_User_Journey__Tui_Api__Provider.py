# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api/core/user_journey tests: User_Journey__Tui_Api__Provider
# dispatch() is exercised against a real Conductor__Client subclass that returns
# canned suite snapshots (no HTTP, no mocks). manifest() + workflows are pure.
# The execution-center test proves the provider plugs into the real gating path.
# ═══════════════════════════════════════════════════════════════════════════════

import os

from sgraph_ai_service_playwright__cli.tui.tool_api.core.user_journey.User_Journey__Tui_Api__Provider import (User_Journey__Tui_Api__Provider,
                                                                                                              API_SLUG)
from sgraph_ai_service_playwright__cli.tui.tool_api.core.user_journey.User_Journey__Workflows         import WORKFLOWS, monitor, operate, load

from sg_compute_specs.user_journey.core.clients.Conductor__Client               import Conductor__Client
from sg_compute_specs.user_journey.core.schemas.enums.Enum__Suite__Run__State   import Enum__Suite__Run__State
from sg_compute_specs.user_journey.core.schemas.suite.Schema__Suite__Run__Status import Schema__Suite__Run__Status


class _Canned_Conductor(Conductor__Client):                                       # real subclass; no network, no mocks

    def get_suite(self, suite_run_id):
        status               = Schema__Suite__Run__Status(state=Enum__Suite__Run__State.RUNNING)
        status.counts.passed = 7
        return status

    def start_suite_id(self, suite_id):
        return Schema__Suite__Run__Status(state=Enum__Suite__Run__State.PENDING)

    def stop_suite(self, suite_run_id):
        return Schema__Suite__Run__Status(state=Enum__Suite__Run__State.STOPPED)

    def scale_suite(self, suite_run_id, count, concurrency):
        return Schema__Suite__Run__Status(state=Enum__Suite__Run__State.RUNNING)

    def get_flows(self, suite_run_id):
        return [{'request': {'url': 'https://shop.test/pay'}, 'response': {'status_code': 504}}]


def _provider():
    provider           = User_Journey__Tui_Api__Provider()
    provider.conductor = _Canned_Conductor()
    return provider


class TestManifest:

    def test__action_names_and_tiers(self):
        manifest = _provider().manifest()
        names    = {str(a.name) for a in manifest.actions}
        assert names == {'uj.status', 'uj.flows', 'uj.start', 'uj.stop', 'uj.scale'}
        by_name  = {str(a.name): a for a in manifest.actions}
        assert str(by_name['uj.status'].tier) == 'read_only'
        assert str(by_name['uj.start' ].tier) == 'write'
        assert str(by_name['uj.scale' ].tier) == 'destructive'

    def test__scopes_and_dry_run(self):
        by_name = {str(a.name): a for a in _provider().manifest().actions}
        assert str(by_name['uj.status'].scope.api)        == API_SLUG
        assert str(by_name['uj.status'].scope.capability) == 'read'
        assert str(by_name['uj.scale' ].scope.capability) == 'scale'
        assert by_name['uj.status'].supports_dry_run is False
        assert by_name['uj.scale' ].supports_dry_run is True

    def test__scale_input_schema_has_count(self):
        by_name = {str(a.name): a for a in _provider().manifest().actions}
        properties = by_name['uj.scale'].input_schema['properties']
        assert 'count'       in properties
        assert 'concurrency' in properties


class TestDispatch:

    def test__status_returns_counts(self):
        result = _provider().dispatch('uj.status', {'suite_run_id': 'r1'})
        assert result.ok is True
        assert int(result.data['result']['counts']['passed']) == 7

    def test__flows_passthrough(self):
        result = _provider().dispatch('uj.flows', {'suite_run_id': 'r1'})
        assert result.ok is True
        assert result.data['result']['flows'][0]['response']['status_code'] == 504

    def test__start_and_stop_and_scale(self):
        provider = _provider()
        assert provider.dispatch('uj.start', {'suite_id': 'nightly'}).ok is True
        assert provider.dispatch('uj.stop',  {'suite_run_id': 'r1'}).ok  is True
        assert provider.dispatch('uj.scale', {'suite_run_id': 'r1', 'count': 500, 'concurrency': 50}).ok is True

    def test__unknown_action_is_error(self):
        result = _provider().dispatch('uj.bogus', {})
        assert result.ok is False
        assert 'unknown action' in result.error

    def test__scale_dry_run_preview(self):
        preview = _provider().dry_run('uj.scale', {'suite_run_id': 'r1', 'count': 500, 'concurrency': 50})
        assert preview['target_count']       == 500
        assert preview['target_concurrency'] == 50


class TestWorkflows:

    def test__monitor_is_read_only(self):
        caps = {str(g.scope.capability) for g in monitor().grants}
        assert caps == {'read'}

    def test__operate_adds_write(self):
        caps = {str(g.scope.capability) for g in operate().grants}
        assert caps == {'read', 'write'}

    def test__load_adds_scale(self):
        caps = {str(g.scope.capability) for g in load().grants}
        assert caps == {'read', 'write', 'scale'}

    def test__registry_has_three(self):
        assert set(WORKFLOWS.keys()) == {'monitor', 'operate', 'load'}


class TestExecutionCenter:                                                        # the real "talk to the tools" gating path

    def _center(self, tmp_path):
        from sgraph_ai_service_playwright__cli.aws.creds.service.Creds__Scope__Catalogue        import Creds__Scope__Catalogue
        from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Execution_Center   import Tui_Api__Execution_Center
        from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Privilege__Resolver import Tui_Api__Privilege__Resolver
        from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Registry           import Tui_Api__Registry
        resolver = Tui_Api__Privilege__Resolver(creds_catalogue=Creds__Scope__Catalogue(catalogue_path=str(tmp_path / 's.json')))
        return Tui_Api__Execution_Center(registry=Tui_Api__Registry().register(self._provider()),
                                         resolver=resolver, mutation_env='SG_UJ_TEST_MUT')

    def _provider(self):
        provider           = User_Journey__Tui_Api__Provider()
        provider.conductor = _Canned_Conductor()
        return provider

    def test__read_action_passes(self, tmp_path):
        result = self._center(tmp_path).execute(API_SLUG, 'uj.status', {'suite_run_id': 'r1'})
        assert result.ok is True
        assert int(result.data['result']['counts']['passed']) == 7

    def test__scale_is_gated_to_dry_run_without_mutation_env(self, tmp_path):
        os.environ.pop('SG_UJ_TEST_MUT', None)
        gated = self._center(tmp_path).execute(API_SLUG, 'uj.scale',
                                               {'suite_run_id': 'r1', 'count': 500, 'concurrency': 50})
        assert gated.ok      is False                                             # DESTRUCTIVE, no env, no confirm
        assert gated.dry_run is True
