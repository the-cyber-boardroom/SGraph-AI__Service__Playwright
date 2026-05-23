# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — aws/bedrock/chat: Chat__Backend__Bedrock (plan 07 seam, end-to-end)
# Proves the NEUTRAL Chat__Engine drives the Bedrock adapter: streaming + the agentic
# tool loop run through the adapter's wire-shaping (neutral → Converse blocks →
# neutral) over the scripted Bedrock in-memory source and the REAL S3 tool provider
# via the execution center. No AWS, no boto3, no mocks, no Textual. 3.11.
# ═══════════════════════════════════════════════════════════════════════════════

from tests.unit.sgraph_ai_service_playwright__cli.aws.s3.service.S3__AWS__Client__In_Memory import S3__AWS__Client__In_Memory

from sgraph_ai_service_playwright__cli.aws.bedrock.chat.Chat__Backend__Bedrock        import Chat__Backend__Bedrock
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.source.Bedrock__Chat__In_Memory import Bedrock__Chat__In_Memory
from sgraph_ai_service_playwright__cli.aws.s3.tui_api.S3__Tui_Api__Provider           import S3__Tui_Api__Provider
from sgraph_ai_service_playwright__cli.aws.creds.service.Creds__Scope__Catalogue      import Creds__Scope__Catalogue
from sgraph_ai_service_playwright__cli.tui.chat.service.Chat__Engine                  import Chat__Engine
from sgraph_ai_service_playwright__cli.tui.chat.service.Chat__Tool__Builder           import Chat__Tool__Builder
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Execution_Center import Tui_Api__Execution_Center
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Loadout__Assembler import Tui_Api__Loadout__Assembler
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Privilege__Resolver import Tui_Api__Privilege__Resolver
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Registry         import Tui_Api__Registry


def _backend():
    return Chat__Backend__Bedrock(source=Bedrock__Chat__In_Memory(), region='us-east-1')


# ── streaming through the adapter ──────────────────────────────────────────────────

def test_stream_turn_through_bedrock_adapter():
    backend = _backend()
    backend.source.scripted = [('the wildcard is not resolving alice', 80, 40, 300)]
    engine  = Chat__Engine(backend=backend)
    session = engine.new_session(model_id='default')

    chunks = []
    turn   = engine.send_turn(session, 'why is alice dormant?', on_delta=chunks.append)

    assert 'wildcard is not resolving alice' in ''.join(chunks)
    assert turn.input_tokens == 80 and turn.output_tokens == 40
    assert turn.cost_usd > 0                                                      # Nova pricing via the cost calculator
    assert backend.id() == 'bedrock'
    # the adapter resolved the neutral alias and shaped the messages to Converse form
    model_id, wire_messages, system = backend.source.calls[0]
    assert model_id == 'amazon.nova-lite-v1:0'                                    # 'default' alias → Bedrock model id
    assert wire_messages[0]['content'][0]['text'] == 'why is alice dormant?'      # neutral text → Converse {text}


# ── agentic loop through the adapter, real S3 tool ──────────────────────────────────

def _tools(tmp_path):
    registry  = Tui_Api__Registry().register(S3__Tui_Api__Provider(client=S3__AWS__Client__In_Memory().add_bucket('demo-bucket')))
    resolver  = Tui_Api__Privilege__Resolver(creds_catalogue=Creds__Scope__Catalogue(catalogue_path=str(tmp_path / 's.json')))
    center    = Tui_Api__Execution_Center(registry=registry, resolver=resolver)
    builder   = Chat__Tool__Builder()
    granted   = Tui_Api__Loadout__Assembler().granted_actions(
                    Tui_Api__Loadout__Assembler().from_tools('sg-aws.s3:read'), registry, resolver)
    tools, name_map = builder.build(granted)
    return center, tools, name_map, builder


def test_agentic_loop_through_bedrock_adapter(tmp_path):
    center, tools, name_map, builder = _tools(tmp_path)
    backend   = _backend()
    tool_name = builder.tool_name('sg-aws.s3', 'list_buckets')
    backend.source.scripted_turns = [
        {'stop_reason': 'tool_use',
         'content'    : [{'toolUse': {'toolUseId': 't1', 'name': tool_name, 'input': {}}}],
         'input_tokens': 100, 'output_tokens': 20, 'latency_ms': 200},
        {'stop_reason': 'end_turn', 'content': [{'text': 'You have one bucket: demo-bucket.'}],
         'input_tokens': 150, 'output_tokens': 30, 'latency_ms': 250},
    ]
    engine  = Chat__Engine(backend=backend)
    session = engine.new_session(model_id='default')
    turn    = engine.send_turn_agentic(session, 'how many buckets?', center, tools, name_map)

    assert turn.model_calls  == 2 and turn.tool_calls == 1
    assert turn.input_tokens == 250 and turn.output_tokens == 50
    assert turn.cost_usd      > 0
    assert 'demo-bucket' in session.messages[-1].content[0].text
    assert any(str(call.action_ref) == 'list_buckets' for call in center.log)     # ran + audited through the center
    assert len(turn.tool_log) == 1 and str(turn.tool_log[0].status) == 'success'

    # the adapter shaped the toolConfig and fed the toolResult back as Converse blocks
    _, _, _, tool_config = backend.source.turn_calls[0]
    assert tool_config['tools'][0]['toolSpec']['name'] == tool_name               # neutral tool → Bedrock toolSpec
    _, second_wire, _, _ = backend.source.turn_calls[1]
    assert second_wire[-1]['content'][0]['toolResult']['status'] == 'success'     # neutral tool_result → Converse toolResult
