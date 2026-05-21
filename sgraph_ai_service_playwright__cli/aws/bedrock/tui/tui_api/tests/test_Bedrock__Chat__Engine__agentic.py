# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — aws/bedrock/tui/tui_api tests: the agentic Converse tool-use loop (C-TL1)
# Drives engine.send_turn_agentic with an in-memory source scripting a tool_use →
# end_turn sequence (no AWS, no mocks). The S3 read tool is executed through the
# execution center (gated + audited); per-turn cost sums all model + tool sub-calls.
# ═══════════════════════════════════════════════════════════════════════════════

from tests.unit.sgraph_ai_service_playwright__cli.aws.s3.service.S3__AWS__Client__In_Memory import S3__AWS__Client__In_Memory

from sgraph_ai_service_playwright__cli.aws.bedrock.tui.service.Bedrock__Chat__Engine        import Bedrock__Chat__Engine
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.source.Bedrock__Chat__In_Memory      import Bedrock__Chat__In_Memory
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.tui_api.Bedrock__Tool_Config__Builder import Bedrock__Tool_Config__Builder
from sgraph_ai_service_playwright__cli.aws.creds.service.Creds__Scope__Catalogue            import Creds__Scope__Catalogue
from sgraph_ai_service_playwright__cli.aws.s3.tui_api.S3__Tui_Api__Provider                 import S3__Tui_Api__Provider
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Execution_Center       import Tui_Api__Execution_Center
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Privilege__Resolver    import Tui_Api__Privilege__Resolver
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Registry               import Tui_Api__Registry


def _harness(tmp_path):
    provider = S3__Tui_Api__Provider(client=S3__AWS__Client__In_Memory().add_bucket('demo-bucket'))
    registry = Tui_Api__Registry().register(provider)
    resolver = Tui_Api__Privilege__Resolver(creds_catalogue=Creds__Scope__Catalogue(catalogue_path=str(tmp_path / 's.json')))
    center   = Tui_Api__Execution_Center(registry=registry, resolver=resolver)
    builder  = Bedrock__Tool_Config__Builder()
    tool_config, name_map = builder.build([('sg-aws.s3', a) for a in provider.manifest().actions])
    return registry, center, tool_config, name_map, builder


def test_loop_executes_tool_then_finishes(tmp_path):
    registry, center, tool_config, name_map, builder = _harness(tmp_path)
    source = Bedrock__Chat__In_Memory()
    source.scripted_turns = [
        {'stop_reason': 'tool_use',
         'content'    : [{'toolUse': {'toolUseId': 't1', 'name': builder.tool_name('sg-aws.s3', 'list_buckets'), 'input': {}}}],
         'input_tokens': 100, 'output_tokens': 20, 'latency_ms': 200},
        {'stop_reason': 'end_turn',
         'content'    : [{'text': 'You have one bucket: demo-bucket.'}],
         'input_tokens': 150, 'output_tokens': 30, 'latency_ms': 250},
    ]
    engine  = Bedrock__Chat__Engine(source=source)
    session = engine.new_session(region='us-east-1', model_alias='lite')
    turn    = engine.send_turn_agentic(session, 'how many buckets do I have?', registry, center, tool_config, name_map)

    assert turn.model_calls   == 2                                                # tool_use round-trip + final
    assert turn.tool_calls    == 1
    assert turn.input_tokens  == 250 and turn.output_tokens == 50                  # summed across both Converse calls
    assert turn.cost_usd       > 0
    assert 'demo-bucket' in session.messages[-1].text                             # the final assistant answer
    assert any(str(call.action_ref) == 'list_buckets' for call in center.log)     # the tool ran + was audited
    assert session.turn_count == 1


def test_loop_with_no_tool_just_answers(tmp_path):
    registry, center, tool_config, name_map, _ = _harness(tmp_path)
    source = Bedrock__Chat__In_Memory()
    source.scripted_turns = [{'stop_reason': 'end_turn', 'content': [{'text': 'hello'}],
                              'input_tokens': 10, 'output_tokens': 5, 'latency_ms': 50}]
    engine  = Bedrock__Chat__Engine(source=source)
    session = engine.new_session(region='us-east-1', model_alias='lite')
    turn    = engine.send_turn_agentic(session, 'hi', registry, center, tool_config, name_map)
    assert turn.model_calls == 1 and turn.tool_calls == 0
    assert session.messages[-1].text == 'hello'


def test_unknown_tool_is_reported_not_crash(tmp_path):
    registry, center, tool_config, name_map, _ = _harness(tmp_path)
    source = Bedrock__Chat__In_Memory()
    source.scripted_turns = [
        {'stop_reason': 'tool_use', 'content': [{'toolUse': {'toolUseId': 't1', 'name': 'bogus_tool', 'input': {}}}],
         'input_tokens': 50, 'output_tokens': 10, 'latency_ms': 100},
        {'stop_reason': 'end_turn', 'content': [{'text': 'sorry, could not do that'}],
         'input_tokens': 60, 'output_tokens': 10, 'latency_ms': 100},
    ]
    engine  = Bedrock__Chat__Engine(source=source)
    session = engine.new_session(region='us-east-1', model_alias='lite')
    turn    = engine.send_turn_agentic(session, 'x', registry, center, tool_config, name_map)
    assert turn.tool_calls == 1                                                   # attempted
    assert session.messages[-1].text == 'sorry, could not do that'
