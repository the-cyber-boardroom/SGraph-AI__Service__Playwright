# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — bedrock tui: inspector tool-call rendering (C-TL3)
# inspector_detail_markup shows a tool-calls section for agentic turns and omits it
# for plain streaming turns. Pure render — 3.11.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.aws.bedrock.tui.schemas.List__Bedrock__Chat__Tool_Call   import List__Bedrock__Chat__Tool_Call
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.schemas.Schema__Bedrock__Chat__Tool_Call import Schema__Bedrock__Chat__Tool_Call
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.schemas.Schema__Bedrock__Chat__Turn      import Schema__Bedrock__Chat__Turn
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.screens.Bedrock__Chat__Render            import inspector_detail_markup


def test_inspector_detail_renders_tool_calls():
    tool_log = List__Bedrock__Chat__Tool_Call()
    tool_log.append(Schema__Bedrock__Chat__Tool_Call(name='core_vfs__vfs_read', input_json='{"path": "notes.md"}',
                                                    status='success', result_json='{"result": "the answer is 42"}'))
    turn = Schema__Bedrock__Chat__Turn(model_id='amazon.nova-lite-v1:0', input_tokens=250, output_tokens=50,
                                      cost_usd=0.0001, latency_ms=400, response_text='Your note says 42.',
                                      model_calls=2, tool_calls=1, tool_log=tool_log)
    markup = inspector_detail_markup(turn, 0)
    assert 'tool calls (1)' in markup
    assert 'core_vfs__vfs_read' in markup
    assert 'notes.md' in markup
    assert '2 model · 1 tools' in markup


def test_inspector_detail_omits_tools_for_streaming_turn():
    turn = Schema__Bedrock__Chat__Turn(model_id='amazon.nova-lite-v1:0', input_tokens=10, output_tokens=5,
                                      cost_usd=0.0, latency_ms=50, response_text='hi')
    assert 'tool calls' not in inspector_detail_markup(turn, 0)
