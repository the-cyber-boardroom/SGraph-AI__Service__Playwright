# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Sentinel__Chat (agentic chat over the read-only TUI API)
# Uses the neutral scripted Chat__Backend__In_Memory (NOT a mock): scripts a tool_use
# turn then a final-text turn, and asserts the engine actually executed the Sentinel
# tool against live (in-memory) state and produced a grounded answer. No AWS, no LLM.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.sentinel.schemas.Schema__Sentinel__Log_Record      import Schema__Sentinel__Log_Record
from sgraph_ai_service_playwright__cli.sentinel.service.log_sink.InMemory__Log__Sink       import InMemory__Log__Sink
from sgraph_ai_service_playwright__cli.sentinel.tui.chat.Sentinel__Chat                    import Sentinel__Chat
from sgraph_ai_service_playwright__cli.sentinel.tui.source.Sentinel__TUI__Source           import Sentinel__TUI__Source
from sgraph_ai_service_playwright__cli.sentinel.tui.tui_api.Sentinel__Tui_Api__Provider    import SLUG
from sgraph_ai_service_playwright__cli.tui.chat.backend.Chat__Backend__In_Memory           import Chat__Backend__In_Memory
from sgraph_ai_service_playwright__cli.tui.chat.schemas.Schema__Chat__Content              import Schema__Chat__Content
from sgraph_ai_service_playwright__cli.tui.chat.schemas.Schema__Chat__Tool_Use             import Schema__Chat__Tool_Use
from sgraph_ai_service_playwright__cli.tui.chat.schemas.Schema__Chat__Turn__Result         import Schema__Chat__Turn__Result
from sgraph_ai_service_playwright__cli.tui.chat.schemas.Schema__Chat__Usage                import Schema__Chat__Usage
from sgraph_ai_service_playwright__cli.tui.chat.service.Chat__Tool__Builder                import Chat__Tool__Builder


def _source_with_block():
    sink = InMemory__Log__Sink()
    sink.write(Schema__Sentinel__Log_Record(request_id='sn-1', received_at='2026-05-23T14:30:00Z', method='GET',
                                            path='/etc/passwd', host='h', source_ip='abc', verdict='block',
                                            reason='path never valid', rule_id='0012', http_status=403, enforced=True))
    return Sentinel__TUI__Source(log_sink=sink)


def _scripted_backend(action: str) -> Chat__Backend__In_Memory:
    tool_name = Chat__Tool__Builder().tool_name(SLUG, action)
    use = Schema__Chat__Turn__Result(stop_reason='tool_use',
                                     usage=Schema__Chat__Usage(input_tokens=100, output_tokens=20, latency_ms=50))
    use.content.append(Schema__Chat__Content(tool_use=Schema__Chat__Tool_Use(id='t1', name=tool_name, input={})))
    end = Schema__Chat__Turn__Result(stop_reason='end_turn',
                                     usage=Schema__Chat__Usage(input_tokens=120, output_tokens=30, latency_ms=60))
    end.content.append(Schema__Chat__Content(text='There is 1 blocked request (rule 0012).'))
    backend = Chat__Backend__In_Memory()
    backend.scripted_turns = [use, end]
    return backend


class TestAsk:
    def test_chat_calls_a_tool_and_answers(self):
        chatter = Sentinel__Chat(source=_source_with_block(), backend=_scripted_backend('blocks_list'))
        session = chatter.new_session()
        turn    = chatter.ask(session, 'how many blocks are there?')
        assert turn.tool_calls == 1
        assert turn.model_calls == 2                                                 # tool_use turn + final turn
        assert 'blocked request' in turn.response_text
        assert turn.tool_log[0].status == 'success'                                  # the Sentinel tool actually ran

    def test_tool_ran_against_real_state(self):
        chatter = Sentinel__Chat(source=_source_with_block(), backend=_scripted_backend('status'))
        session = chatter.new_session()
        turn    = chatter.ask(session, 'what is the status?')
        import json
        result = json.loads(turn.tool_log[0].result_json)
        assert result['result']['status']['block_count'] == 1                        # grounded in the in-memory sink


class TestSession:
    def test_new_session_uses_the_model_and_system_prompt(self):
        chatter = Sentinel__Chat(source=_source_with_block(), backend=_scripted_backend('status'), model='micro')
        session = chatter.new_session()
        assert str(session.model_id) == 'micro'
        assert 'SG/Sentinel assistant' in session.system_prompt
        assert 'rules_list' in session.system_prompt                                 # the api SKILL is injected
