# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — aws/bedrock/tui/tui_api tests: loadout → toolConfig → agentic loop (C-TL2)
# The full consumer chain: a --tools loadout resolves granted actions → the Bedrock
# toolConfig builder → the engine's agentic loop executes the scripted tool_use
# through the execution center. No AWS, no mocks. Pure — 3.11.
# ═══════════════════════════════════════════════════════════════════════════════

from tests.unit.sgraph_ai_service_playwright__cli.aws.s3.service.S3__AWS__Client__In_Memory import S3__AWS__Client__In_Memory

from sgraph_ai_service_playwright__cli.aws.bedrock.tui.service.Bedrock__Chat__Engine        import Bedrock__Chat__Engine
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.source.Bedrock__Chat__In_Memory      import Bedrock__Chat__In_Memory
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.tui_api.Bedrock__Tool_Config__Builder import Bedrock__Tool_Config__Builder
from sgraph_ai_service_playwright__cli.aws.creds.service.Creds__Scope__Catalogue            import Creds__Scope__Catalogue
from sgraph_ai_service_playwright__cli.aws.s3.tui_api.S3__Tui_Api__Provider                 import S3__Tui_Api__Provider
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Execution_Center       import Tui_Api__Execution_Center
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Loadout__Assembler     import Tui_Api__Loadout__Assembler
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Privilege__Resolver    import Tui_Api__Privilege__Resolver
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Registry               import Tui_Api__Registry


def test_tools_flag_drives_the_agentic_loop(tmp_path):
    registry  = Tui_Api__Registry().register(S3__Tui_Api__Provider(client=S3__AWS__Client__In_Memory().add_bucket('demo-bucket')))
    resolver  = Tui_Api__Privilege__Resolver(creds_catalogue=Creds__Scope__Catalogue(catalogue_path=str(tmp_path / 's.json')))
    center    = Tui_Api__Execution_Center(registry=registry, resolver=resolver)
    assembler = Tui_Api__Loadout__Assembler()
    builder   = Bedrock__Tool_Config__Builder()

    loadout               = assembler.from_tools('sg-aws.s3:read')                # the user grants read-only s3
    granted               = assembler.granted_actions(loadout, registry, resolver)
    tool_config, name_map = builder.build(granted)
    assert len(tool_config['tools']) == 3                                         # only the granted (read) actions reach the model

    source = Bedrock__Chat__In_Memory()
    source.scripted_turns = [
        {'stop_reason': 'tool_use',
         'content'    : [{'toolUse': {'toolUseId': 't1', 'name': builder.tool_name('sg-aws.s3', 'list_buckets'), 'input': {}}}],
         'input_tokens': 100, 'output_tokens': 20, 'latency_ms': 200},
        {'stop_reason': 'end_turn', 'content': [{'text': 'You have one bucket: demo-bucket.'}],
         'input_tokens': 150, 'output_tokens': 30, 'latency_ms': 250},
    ]
    engine  = Bedrock__Chat__Engine(source=source)
    session = engine.new_session(region='us-east-1', model_alias='lite')
    turn    = engine.send_turn_agentic(session, 'how many buckets?', registry, center, tool_config, name_map)

    assert turn.tool_calls == 1 and turn.model_calls == 2
    assert 'demo-bucket' in session.messages[-1].text
    assert any(str(call.action_ref) == 'list_buckets' for call in center.log)


def test_no_grant_means_no_tools_reach_the_model(tmp_path):
    registry  = Tui_Api__Registry().register(S3__Tui_Api__Provider(client=S3__AWS__Client__In_Memory()))
    resolver  = Tui_Api__Privilege__Resolver(creds_catalogue=Creds__Scope__Catalogue(catalogue_path=str(tmp_path / 's.json')))
    assembler = Tui_Api__Loadout__Assembler()
    loadout   = assembler.from_tools('sg-aws.s3:write')                           # write doesn't cover the read-only s3 actions
    tool_config, _ = Bedrock__Tool_Config__Builder().build(assembler.granted_actions(loadout, registry, resolver))
    assert tool_config['tools'] == []                                             # the model is offered nothing
