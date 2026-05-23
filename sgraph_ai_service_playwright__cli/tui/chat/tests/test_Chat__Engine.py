# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/chat tests: Chat__Engine (neutral, backend-agnostic)
# Streaming + the agentic tool loop over the in-memory backend, driving the REAL S3
# tool provider through the execution center. No AWS, no mocks, no Textual. 3.11.
# ═══════════════════════════════════════════════════════════════════════════════

from tests.unit.sgraph_ai_service_playwright__cli.aws.s3.service.S3__AWS__Client__In_Memory import S3__AWS__Client__In_Memory

from sgraph_ai_service_playwright__cli.aws.s3.tui_api.S3__Tui_Api__Provider              import S3__Tui_Api__Provider
from sgraph_ai_service_playwright__cli.aws.creds.service.Creds__Scope__Catalogue         import Creds__Scope__Catalogue
from sgraph_ai_service_playwright__cli.tui.chat.backend.Chat__Backend__In_Memory         import Chat__Backend__In_Memory
from sgraph_ai_service_playwright__cli.tui.chat.schemas.Schema__Chat__Content            import Schema__Chat__Content
from sgraph_ai_service_playwright__cli.tui.chat.schemas.Schema__Chat__Tool_Use           import Schema__Chat__Tool_Use
from sgraph_ai_service_playwright__cli.tui.chat.schemas.Schema__Chat__Turn__Result       import Schema__Chat__Turn__Result
from sgraph_ai_service_playwright__cli.tui.chat.schemas.Schema__Chat__Usage              import Schema__Chat__Usage
from sgraph_ai_service_playwright__cli.tui.chat.service.Chat__Engine                     import Chat__Engine
from sgraph_ai_service_playwright__cli.tui.chat.service.Chat__Tool__Builder              import Chat__Tool__Builder
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Execution_Center    import Tui_Api__Execution_Center
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Loadout__Assembler  import Tui_Api__Loadout__Assembler
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Privilege__Resolver import Tui_Api__Privilege__Resolver
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Registry            import Tui_Api__Registry


# ── streaming ────────────────────────────────────────────────────────────────────

def test_send_turn_streams_and_records_cost():
    backend = Chat__Backend__In_Memory()
    backend.scripted_stream = [('the wildcard is not resolving alice', 80, 40, 300)]
    engine  = Chat__Engine(backend=backend)
    session = engine.new_session(model_id='nova-lite')

    chunks = []
    turn   = engine.send_turn(session, 'why is alice dormant?', on_delta=chunks.append)

    assert 'wildcard is not resolving alice' in ''.join(chunks)
    assert turn.input_tokens == 80 and turn.output_tokens == 40
    assert turn.cost_usd > 0                                                      # backend.cost summed the usage
    assert session.turn_count == 1 and session.total_cost_usd == turn.cost_usd
    assert session.messages[-1].content[0].text.strip() == 'the wildcard is not resolving alice'


# ── agentic loop (neutral) with the real S3 tool ──────────────────────────────────

def _tools(tmp_path):
    registry  = Tui_Api__Registry().register(S3__Tui_Api__Provider(client=S3__AWS__Client__In_Memory().add_bucket('demo-bucket')))
    resolver  = Tui_Api__Privilege__Resolver(creds_catalogue=Creds__Scope__Catalogue(catalogue_path=str(tmp_path / 's.json')))
    center    = Tui_Api__Execution_Center(registry=registry, resolver=resolver)
    builder   = Chat__Tool__Builder()
    granted   = Tui_Api__Loadout__Assembler().granted_actions(
                    Tui_Api__Loadout__Assembler().from_tools('sg-aws.s3:read'), registry, resolver)
    tools, name_map = builder.build(granted)
    return center, tools, name_map, builder


def test_agentic_loop_calls_a_tool_then_answers(tmp_path):
    center, tools, name_map, builder = _tools(tmp_path)
    backend = Chat__Backend__In_Memory()

    tool_use_turn = Schema__Chat__Turn__Result(stop_reason='tool_use',
                                              usage=Schema__Chat__Usage(input_tokens=100, output_tokens=20, latency_ms=200))
    tool_use_turn.content.append(Schema__Chat__Content(
        tool_use=Schema__Chat__Tool_Use(id='t1', name=builder.tool_name('sg-aws.s3', 'list_buckets'), input={})))
    end_turn = Schema__Chat__Turn__Result(stop_reason='end_turn',
                                         usage=Schema__Chat__Usage(input_tokens=150, output_tokens=30, latency_ms=250))
    end_turn.content.append(Schema__Chat__Content(text='You have one bucket: demo-bucket.'))
    backend.scripted_turns = [tool_use_turn, end_turn]

    engine  = Chat__Engine(backend=backend)
    session = engine.new_session(model_id='nova-lite')
    turn    = engine.send_turn_agentic(session, 'how many buckets?', center, tools, name_map)

    assert turn.model_calls   == 2 and turn.tool_calls == 1
    assert turn.input_tokens  == 250 and turn.output_tokens == 50               # summed across both converse calls
    assert turn.cost_usd       > 0
    assert 'demo-bucket' in session.messages[-1].content[0].text
    assert any(str(call.action_ref) == 'list_buckets' for call in center.log)   # ran + audited through the center
    assert len(turn.tool_log) == 1 and str(turn.tool_log[0].status) == 'success'
    # the backend received NEUTRAL tool specs (not a Bedrock toolConfig)
    assert backend.turn_calls[0][3] is tools


def test_agentic_loop_no_tool_just_answers(tmp_path):
    center, tools, name_map, _ = _tools(tmp_path)
    backend = Chat__Backend__In_Memory()
    end_turn = Schema__Chat__Turn__Result(stop_reason='end_turn',
                                         usage=Schema__Chat__Usage(input_tokens=10, output_tokens=5, latency_ms=50))
    end_turn.content.append(Schema__Chat__Content(text='hello'))
    backend.scripted_turns = [end_turn]
    engine  = Chat__Engine(backend=backend)
    session = engine.new_session(model_id='nova-lite')
    turn    = engine.send_turn_agentic(session, 'hi', center, tools, name_map)
    assert turn.model_calls == 1 and turn.tool_calls == 0
    assert session.messages[-1].content[0].text == 'hello'
