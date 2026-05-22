# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api tests: contract gate (the automated B5 tester)
# Runs the reusable contract asserts against the S3 provider (3.11). The VFS provider
# is exercised by the same asserts in its own 3.12-gated test.
# ═══════════════════════════════════════════════════════════════════════════════

from tests.unit.sgraph_ai_service_playwright__cli.aws.s3.service.S3__AWS__Client__In_Memory import S3__AWS__Client__In_Memory

from sgraph_ai_service_playwright__cli.aws.s3.tui_api.S3__Tui_Api__Provider             import S3__Tui_Api__Provider
from sgraph_ai_service_playwright__cli.tui.tool_api.testing.Tui_Api__Contract__Asserts  import Tui_Api__Contract__Asserts


def test_s3_provider_satisfies_contract():
    provider = S3__Tui_Api__Provider(client=S3__AWS__Client__In_Memory())
    Tui_Api__Contract__Asserts().assert_ok(provider)


def test_s3_skills_name_every_action():
    provider = S3__Tui_Api__Provider(client=S3__AWS__Client__In_Memory())
    api_doc  = provider.skills()['api']
    for action in provider.manifest().actions:
        assert str(action.name) in api_doc
