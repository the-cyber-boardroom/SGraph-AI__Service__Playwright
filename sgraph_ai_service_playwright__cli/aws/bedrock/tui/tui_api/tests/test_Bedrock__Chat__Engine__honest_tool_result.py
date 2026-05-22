# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — bedrock tui: gated tool results are fed back honestly (#1)
# When a WRITE tool is gated (no ALLOW_MUTATIONS), the toolResult sent back to the
# model carries the real error (so it can't narrate false success) and the action did
# NOT run. Uses a tiny in-test WRITE provider — no memory_fs, no AWS. Pure — 3.11.
# ═══════════════════════════════════════════════════════════════════════════════

import os

from sgraph_ai_service_playwright__cli.aws.bedrock.tui.service.Bedrock__Chat__Engine        import Bedrock__Chat__Engine
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.source.Bedrock__Chat__In_Memory      import Bedrock__Chat__In_Memory
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.tui_api.Bedrock__Tool_Config__Builder import Bedrock__Tool_Config__Builder
from sgraph_ai_service_playwright__cli.aws.creds.service.Creds__Scope__Catalogue            import Creds__Scope__Catalogue
from sgraph_ai_service_playwright__cli.tui.tool_api.enums.Enum__Tui_Api__Tier               import Enum__Tui_Api__Tier
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.List__Tui_Api__Action            import List__Tui_Api__Action
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.List__Tui_Api__Tier              import List__Tui_Api__Tier
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Action          import Schema__Tui_Api__Action
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Manifest        import Schema__Tui_Api__Manifest
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Result          import Schema__Tui_Api__Result
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Scope           import Schema__Tui_Api__Scope
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Execution_Center        import Tui_Api__Execution_Center
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Privilege__Resolver     import Tui_Api__Privilege__Resolver
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Provider                import Tui_Api__Provider
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Registry                import Tui_Api__Registry


class _Writer(Tui_Api__Provider):
    written : bool = False

    def manifest(self):
        actions = List__Tui_Api__Action()
        actions.append(Schema__Tui_Api__Action(name='save', tier=Enum__Tui_Api__Tier.WRITE,
                                              scope=Schema__Tui_Api__Scope(api='demo.writer', capability='write'),
                                              input_schema={'type': 'object', 'properties': {}}, supports_dry_run=True))
        tiers = List__Tui_Api__Tier(); tiers.append(Enum__Tui_Api__Tier.WRITE)
        return Schema__Tui_Api__Manifest(slug='demo.writer', tool='demo', name='Writer', tiers=tiers, actions=actions)

    def dry_run(self, action, params):
        return {'would_write': True}

    def dispatch(self, action, params):
        self.written = True
        return Schema__Tui_Api__Result(ok=True, data={'written': True})


def test_gated_write_is_refused_and_reported_truthfully(tmp_path):
    os.environ.pop('SG_X_MUT', None)
    provider = _Writer()
    registry = Tui_Api__Registry().register(provider)
    resolver = Tui_Api__Privilege__Resolver(creds_catalogue=Creds__Scope__Catalogue(catalogue_path=str(tmp_path / 's.json')))
    center   = Tui_Api__Execution_Center(registry=registry, resolver=resolver, mutation_env='SG_X_MUT')
    builder  = Bedrock__Tool_Config__Builder()
    tool_config, name_map = builder.build([('demo.writer', provider.manifest().actions[0])])

    source = Bedrock__Chat__In_Memory()
    source.scripted_turns = [
        {'stop_reason': 'tool_use',
         'content': [{'toolUse': {'toolUseId': 't1', 'name': builder.tool_name('demo.writer', 'save'), 'input': {}}}],
         'input_tokens': 50, 'output_tokens': 10, 'latency_ms': 100},
        {'stop_reason': 'end_turn', 'content': [{'text': 'I could not save it.'}],
         'input_tokens': 60, 'output_tokens': 10, 'latency_ms': 100},
    ]
    engine  = Bedrock__Chat__Engine(source=source)
    session = engine.new_session(region='us-east-1', model_alias='lite')
    turn    = engine.send_turn_agentic(session, 'save it', registry, center, tool_config, name_map)

    assert provider.written is False                                              # the WRITE was gated — it did NOT happen
    second_call_messages = source.turn_calls[1][1]                                # the toolResult fed into the 2nd Converse call
    tool_result = second_call_messages[-1]['content'][0]['toolResult']
    assert tool_result['status'] == 'error'
    assert 'mutation gate' in str(tool_result['content'][0]['json'])              # the model is told the truth
    assert str(turn.tool_log[0].status) == 'error'
    assert 'mutation gate' in turn.tool_log[0].result_json
