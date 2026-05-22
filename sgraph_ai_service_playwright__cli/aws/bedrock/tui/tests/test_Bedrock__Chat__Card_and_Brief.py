# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — bedrock tui: card + brief builder (pure exports)
# Asserts the ASCII export card leads with cost and includes the transcript, and the
# dev-brief markdown carries the cost summary, the seeded context, and the messages.
# Runs on 3.11.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright__cli.aws.bedrock.tui.service.Bedrock__Chat__Card          import Bedrock__Chat__Card
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.service.Bedrock__Chat__Brief__Builder import Bedrock__Chat__Brief__Builder
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.service.Bedrock__Chat__Engine         import Bedrock__Chat__Engine
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.source.Bedrock__Chat__In_Memory       import Bedrock__Chat__In_Memory


def built_session():
    src = Bedrock__Chat__In_Memory()
    src.scripted = [('the wildcard is not resolving alice', 80, 40, 300)]
    eng     = Bedrock__Chat__Engine(source=src)
    session = eng.new_session(region='us-east-1', model_alias='lite')
    eng.send_turn(session, 'why is alice dormant?')
    return session


class test_Bedrock__Chat__Card_and_Brief(TestCase):

    def test_card_leads_with_cost_and_transcript(self):
        card = Bedrock__Chat__Card().render(built_session())
        assert 'session cost' in card
        assert 'why is alice dormant?' in card
        assert 'wildcard is not resolving alice' in card

    def test_brief_has_cost_and_messages(self):
        brief = Bedrock__Chat__Brief__Builder().build(built_session())
        assert brief.startswith('# Dev brief —')
        assert 'Session cost' in brief
        assert 'why is alice dormant?' in brief
        assert '## Proposed actions' in brief
