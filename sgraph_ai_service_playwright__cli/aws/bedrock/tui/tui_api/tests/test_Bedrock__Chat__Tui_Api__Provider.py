# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — aws/bedrock/tui/tui_api tests: Bedrock__Chat__Tui_Api__Provider
# The chat as a TUI API provider, driven over the in-memory chat engine (no AWS, no
# mocks). Proves state() is the live session, send advances it + reports cost, and
# send is gated by the execution center when driven headlessly. Pure — 3.11.
# ═══════════════════════════════════════════════════════════════════════════════

import os

from sgraph_ai_service_playwright__cli.aws.bedrock.tui.service.Bedrock__Chat__Engine   import Bedrock__Chat__Engine
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.source.Bedrock__Chat__In_Memory import Bedrock__Chat__In_Memory
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.tui_api.Bedrock__Chat__Tui_Api__Provider import Bedrock__Chat__Tui_Api__Provider
from sgraph_ai_service_playwright__cli.tui.tool_api.testing.Tui_Api__Contract__Asserts import Tui_Api__Contract__Asserts


def _provider(scripted=None):
    source = Bedrock__Chat__In_Memory()
    source.scripted = list(scripted or [('the wildcard is not resolving alice', 80, 40, 300)])
    provider = Bedrock__Chat__Tui_Api__Provider(engine=Bedrock__Chat__Engine(source=source))
    provider.model_alias = 'lite'
    return provider


def test_state_is_the_live_session():
    state = _provider().state()
    assert state['turns'] == 0 and state['model_alias'] == 'lite' and state['total_cost_usd'] == 0


def test_send_advances_session_and_reports_cost():
    provider = _provider()
    result   = provider.dispatch('send', {'text': 'why is alice dormant?'})
    assert result.ok is True
    assert 'wildcard is not resolving alice' in result.data['result']['assistant_text']
    assert result.cost_usd > 0
    assert provider.state()['turns'] == 1
    assert provider.state()['total_input_tokens'] == 80


def test_set_model_then_clear():
    provider = _provider()
    provider.dispatch('set_model', {'alias': 'pro'})
    assert provider.state()['model_alias'] == 'pro'
    provider.dispatch('send', {'text': 'hi'})
    assert provider.state()['turns'] == 1
    provider.dispatch('clear', {})
    assert provider.state()['turns'] == 0


def test_satisfies_contract():
    Tui_Api__Contract__Asserts().assert_ok(_provider())


def test_send_is_gated_by_execution_center(tmp_path):
    from sgraph_ai_service_playwright__cli.aws.creds.service.Creds__Scope__Catalogue        import Creds__Scope__Catalogue
    from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Execution_Center   import Tui_Api__Execution_Center
    from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Privilege__Resolver import Tui_Api__Privilege__Resolver
    from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Registry           import Tui_Api__Registry

    provider = _provider()
    resolver = Tui_Api__Privilege__Resolver(creds_catalogue=Creds__Scope__Catalogue(catalogue_path=str(tmp_path / 's.json')))
    center   = Tui_Api__Execution_Center(registry=Tui_Api__Registry().register(provider),
                                        resolver=resolver, mutation_env='SG_CHAT_TEST_MUT')
    os.environ.pop('SG_CHAT_TEST_MUT', None)
    result = center.execute('sg-aws.bedrock-chat', 'send', {'text': 'hi'})        # WRITE, no env, no confirm → gated
    assert result.ok is False
    assert provider.state()['turns'] == 0                                         # the send did NOT happen
