# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api/core/user_journey tests: User_Journey__Chat__Tools
# Proves the chat cockpit only ever sees the tools the chosen workflow grants
# (decision #10). Pure in-memory composition — no LLM, no HTTP, no mocks.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.tui.tool_api.core.user_journey.User_Journey__Chat__Tools import User_Journey__Chat__Tools
from sgraph_ai_service_playwright__cli.tui.tool_api.core.user_journey.User_Journey__Workflows   import monitor, operate, load


def _resolver(tmp_path):
    from sgraph_ai_service_playwright__cli.aws.creds.service.Creds__Scope__Catalogue        import Creds__Scope__Catalogue
    from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Privilege__Resolver import Tui_Api__Privilege__Resolver
    return Tui_Api__Privilege__Resolver(creds_catalogue=Creds__Scope__Catalogue(catalogue_path=str(tmp_path / 's.json')))


def _granted_action_names(workflow, tmp_path):
    bridge          = User_Journey__Chat__Tools()
    registry        = bridge.registry()
    tools, name_map = bridge.build_for_workflow(workflow, registry, _resolver(tmp_path))
    return {action for (_slug, action) in name_map.values()}


def test_monitor_grants_read_only(tmp_path):
    names = _granted_action_names(monitor(), tmp_path)
    assert names == {'uj.status', 'uj.flows'}                                      # no start/stop/scale


def test_operate_adds_start_stop(tmp_path):
    names = _granted_action_names(operate(), tmp_path)
    assert {'uj.status', 'uj.flows', 'uj.start', 'uj.stop'} <= names
    assert 'uj.scale' not in names                                                 # scale needs the load workflow


def test_load_grants_scale(tmp_path):
    names = _granted_action_names(load(), tmp_path)
    assert names == {'uj.status', 'uj.flows', 'uj.start', 'uj.stop', 'uj.scale'}


def test_tool_names_are_sanitised(tmp_path):
    bridge          = User_Journey__Chat__Tools()
    registry        = bridge.registry()
    tools, name_map = bridge.build_for_workflow(load(), registry, _resolver(tmp_path))
    for tool in tools:
        assert all(ch.isalnum() or ch in '_-' for ch in str(tool.name))           # valid for Bedrock AND OpenAI
