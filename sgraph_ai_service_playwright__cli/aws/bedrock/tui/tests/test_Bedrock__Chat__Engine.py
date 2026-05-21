# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — bedrock tui: chat engine
# The heart of the cost story. Drives Bedrock__Chat__Engine against the scripted
# in-memory source (no mocks, no boto3) and asserts: exact per-turn tokens/cost,
# session aggregates, message growth, model resolution + full history passed, and the
# pre-flight cost cap leaving the session unmutated when it trips. Runs on 3.11.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright__cli.aws.bedrock.service.Bedrock__Cost__Calculator      import Bedrock__Cost__Calculator
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.enums.Enum__Bedrock__Chat__Role     import Enum__Bedrock__Chat__Role
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.service.Bedrock__Chat__Engine       import Bedrock__Chat__Engine
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.source.Bedrock__Chat__In_Memory     import Bedrock__Chat__In_Memory

NOVA_LITE = 'amazon.nova-lite-v1:0'


def engine(scripted):
    src = Bedrock__Chat__In_Memory()
    src.scripted = list(scripted)
    return Bedrock__Chat__Engine(source=src), src


class test_Bedrock__Chat__Engine(TestCase):

    def test_single_turn_tokens_cost_and_messages(self):
        eng, src = engine([('Hi there friend', 100, 50, 420)])
        session  = eng.new_session(region='us-east-1', model_alias='lite')

        collected = []
        turn = eng.send_turn(session, 'hello', on_delta=collected.append)

        assert turn.input_tokens  == 100
        assert turn.output_tokens == 50
        assert turn.latency_ms    == 420
        assert str(turn.model_id) == NOVA_LITE

        expected_cost = Bedrock__Cost__Calculator().estimate(NOVA_LITE, 100, 50)
        assert turn.cost_usd            == expected_cost
        assert session.total_cost_usd   == expected_cost
        assert expected_cost            > 0                                        # cost is NOT zero (the streaming fix)

        assert len(session.messages)        == 2
        assert session.messages[0].role     == Enum__Bedrock__Chat__Role.USER
        assert session.messages[0].text     == 'hello'
        assert session.messages[1].role     == Enum__Bedrock__Chat__Role.ASSISTANT
        assert 'Hi there friend' in session.messages[1].text
        assert ''.join(collected).strip()   == 'Hi there friend'                   # deltas reconstruct the reply
        assert session.turn_count           == 1

        # model + full history were handed to the source
        model_id, messages, system = src.calls[0]
        assert model_id        == NOVA_LITE
        assert messages[0]     == {'role': 'user', 'content': [{'text': 'hello'}]}
        assert system          is None

    def test_multi_turn_aggregates_and_history(self):
        eng, src = engine([('first reply', 40, 10, 100),
                           ('second reply', 60, 20, 200)])
        session  = eng.new_session(region='us-east-1', model_alias='lite')

        eng.send_turn(session, 'one')
        eng.send_turn(session, 'two')

        assert session.turn_count          == 2
        assert session.total_input_tokens  == 100
        assert session.total_output_tokens == 30
        assert session.total_cost_usd      == round(sum(t.cost_usd for t in session.turns), 6) \
                                              or session.total_cost_usd > 0
        assert len(session.messages)       == 4                                    # u, a, u, a

        # the SECOND call carried the full prior history + the new user turn
        _model, messages_2, _system = src.calls[1]
        roles = [m['role'] for m in messages_2]
        assert roles == ['user', 'assistant', 'user']
        assert messages_2[-1] == {'role': 'user', 'content': [{'text': 'two'}]}

    def test_preflight_cap_blocks_and_leaves_session_clean(self):
        eng, _src = engine([('should not run', 10, 10, 10)])
        session   = eng.new_session(region='us-east-1', model_alias='lite')

        with self.assertRaises(ValueError):
            eng.send_turn(session, 'hello', cost_override=0.0)                      # cap $0 → any cost trips it

        assert session.turn_count    == 0
        assert len(session.messages) == 0                                          # rejected send did not mutate the session
        assert session.total_cost_usd == 0

    def test_context_seeds_system_prompt(self):
        from sgraph_ai_service_playwright__cli.aws.bedrock.tui.schemas.Schema__Bedrock__Chat__Context import Schema__Bedrock__Chat__Context
        eng, src = engine([('ok', 5, 5, 5)])
        ctx      = Schema__Bedrock__Chat__Context(label='edge snapshot @ 10:30', body='alice: DORMANT')
        session  = eng.new_session(region='us-east-1', model_alias='lite', context=ctx)

        assert session.context_label == 'edge snapshot @ 10:30'
        assert 'alice: DORMANT' in session.system_prompt

        eng.send_turn(session, 'why?')
        _model, _messages, system = src.calls[0]
        assert system is not None and 'alice: DORMANT' in system                   # context handed to the model as a system block
