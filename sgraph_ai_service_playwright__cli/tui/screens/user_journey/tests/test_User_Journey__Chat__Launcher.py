# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/screens/user_journey tests: User_Journey__Chat__Launcher.prepare()
# Exercises the whole chat dispatch path with no LLM: a workflow → a scoped tool_config
# + an execution center, then center.execute(...) straight through to the conductor —
# exactly what send_turn_agentic does on a toolUse. Proves workflow scoping AND the
# grant gate (monitor cannot scale). No mocks, no patches, no AWS.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.tui.screens.user_journey.User_Journey__Chat__Launcher import User_Journey__Chat__Launcher

from sg_compute_specs.user_journey.core.clients.Conductor__Client               import Conductor__Client
from sg_compute_specs.user_journey.core.schemas.enums.Enum__Suite__Run__State   import Enum__Suite__Run__State
from sg_compute_specs.user_journey.core.schemas.suite.Schema__Suite__Run__Status import Schema__Suite__Run__Status

API_SLUG = 'browser.user-journey'


class _Canned_Conductor(Conductor__Client):
    def get_suite(self, suite_run_id):
        status          = Schema__Suite__Run__Status(state=Enum__Suite__Run__State.RUNNING)
        status.suite_id = 'checkout-load'
        status.counts.passed = 3
        return status


def _resolver(tmp_path):
    from sgraph_ai_service_playwright__cli.aws.creds.service.Creds__Scope__Catalogue        import Creds__Scope__Catalogue
    from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Privilege__Resolver import Tui_Api__Privilege__Resolver
    return Tui_Api__Privilege__Resolver(creds_catalogue=Creds__Scope__Catalogue(catalogue_path=str(tmp_path / 's.json')))


def _tool_names(tool_config):
    return [tool['toolSpec']['name'] for tool in tool_config['tools']]


def test_monitor_tool_config_is_read_only(tmp_path):
    ctx   = User_Journey__Chat__Launcher().prepare('monitor', conductor=_Canned_Conductor(), resolver=_resolver(tmp_path))
    names = _tool_names(ctx['tool_config'])
    assert any('uj_status' in name for name in names)
    assert any('uj_flows'  in name for name in names)
    assert not any('uj_scale' in name for name in names)                            # the model never even sees scale


def test_load_tool_config_includes_scale(tmp_path):
    ctx   = User_Journey__Chat__Launcher().prepare('load', conductor=_Canned_Conductor(), resolver=_resolver(tmp_path))
    names = _tool_names(ctx['tool_config'])
    assert any('uj_scale' in name for name in names)


def test_center_dispatches_status_to_conductor(tmp_path):                           # what the agentic loop does on a toolUse
    ctx    = User_Journey__Chat__Launcher().prepare('monitor', conductor=_Canned_Conductor(), resolver=_resolver(tmp_path))
    result = ctx['center'].execute(API_SLUG, 'uj.status', {'suite_run_id': 'r1'}, grants=ctx['grants'])
    assert result.ok is True
    assert result.data['result']['suite_id'] == 'checkout-load'


def test_monitor_cannot_scale_grant_gate(tmp_path):
    ctx    = User_Journey__Chat__Launcher().prepare('monitor', conductor=_Canned_Conductor(), resolver=_resolver(tmp_path))
    result = ctx['center'].execute(API_SLUG, 'uj.scale',
                                   {'suite_run_id': 'r1', 'count': 5, 'concurrency': 2}, grants=ctx['grants'])
    assert result.ok is False
    assert 'not granted' in str(result.error)
