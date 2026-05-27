# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/screens/user_journey: User_Journey__Chat__Launcher
# Wires the conversational cockpit: a workflow (monitor < operate < load) → a scoped
# tool_config the model sees + an execution center that gates every dispatch through
# to the conductor. prepare() is the verifiable core — it returns exactly what
# send_turn_agentic needs, and driving center.execute(...) exercises the whole chat
# path (workflow → center → provider → conductor) with no LLM. launch() mirrors the
# Bedrock chat CLI's run_tui: build the engine, build the screen, run it (interactive).
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws.bedrock.tui.tui_api.Bedrock__Tool_Config__Builder           import Bedrock__Tool_Config__Builder
from sgraph_ai_service_playwright__cli.tui.tool_api.core.user_journey.User_Journey__Tui_Api__Provider import User_Journey__Tui_Api__Provider
from sgraph_ai_service_playwright__cli.tui.tool_api.core.user_journey.User_Journey__Workflows         import monitor, operate, load
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Execution_Center                 import Tui_Api__Execution_Center
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Loadout__Assembler               import Tui_Api__Loadout__Assembler
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Privilege__Resolver              import Tui_Api__Privilege__Resolver
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Registry                         import Tui_Api__Registry

_WORKFLOWS = {'monitor': monitor, 'operate': operate, 'load': load}


class User_Journey__Chat__Launcher(Type_Safe):

    def workflow_for(self, name: str):
        return _WORKFLOWS.get(name, monitor)()

    def prepare(self, workflow: str, conductor=None, resolver=None) -> dict:        # verifiable: workflow → screen kwargs + grants
        provider = User_Journey__Tui_Api__Provider()
        if conductor is not None:
            provider.conductor = conductor
        registry  = Tui_Api__Registry().register(provider)
        resolver  = resolver if resolver is not None else Tui_Api__Privilege__Resolver()
        center    = Tui_Api__Execution_Center(registry=registry, resolver=resolver)
        assembler = Tui_Api__Loadout__Assembler()
        loadout   = assembler.from_workflow(self.workflow_for(workflow))
        granted   = assembler.granted_actions(loadout, registry, resolver)
        tool_config, name_map = Bedrock__Tool_Config__Builder().build(granted)      # only granted actions reach the model
        return {'registry'   : registry,    'center'  : center,
                'tool_config': tool_config, 'name_map': name_map, 'grants': loadout.grants}

    def launch(self, workflow: str = 'monitor', conductor=None, model: str = 'default', region: str = '') -> None:
        from sgraph_ai_service_playwright__cli.aws.bedrock.tui.cli.Cli__Bedrock__Chat__Tui import build_engine, resolve_region
        from sgraph_ai_service_playwright__cli.aws.bedrock.tui.screens.Bedrock__Chat__Screen import Bedrock__Chat__Screen
        engine  = build_engine()
        region  = region or resolve_region(engine)
        context = self.prepare(workflow, conductor)
        Bedrock__Chat__Screen(engine, region=region, model_alias=model,
                              registry    = context['registry'],
                              center      = context['center'],
                              tool_config = context['tool_config'],
                              name_map    = context['name_map']).run()
