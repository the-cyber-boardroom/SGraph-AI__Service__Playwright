# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api tests: Tui_Api__Registry
# Explicit registration + lookup. Uses the real S3 provider over the in-memory S3
# client (no mocks, no AWS). Pure — 3.11.
# ═══════════════════════════════════════════════════════════════════════════════

from tests.unit.sgraph_ai_service_playwright__cli.aws.s3.service.S3__AWS__Client__In_Memory import S3__AWS__Client__In_Memory

from sgraph_ai_service_playwright__cli.aws.s3.tui_api.S3__Tui_Api__Provider       import S3__Tui_Api__Provider
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Registry     import Tui_Api__Registry


def _s3_provider():
    client = S3__AWS__Client__In_Memory().add_bucket('demo-bucket')
    return S3__Tui_Api__Provider(client=client)


def test_register_and_lookup():
    registry = Tui_Api__Registry()
    registry.register(_s3_provider())
    assert registry.list_slugs()      == ['sg-aws.s3']
    assert registry.get('sg-aws.s3')  is not None
    assert registry.get('nope')       is None


def test_register_is_chainable_and_idempotent_on_slug():
    registry = Tui_Api__Registry().register(_s3_provider())
    provider = registry.get('sg-aws.s3')
    assert str(provider.manifest().slug) == 'sg-aws.s3'
    assert str(provider.manifest().tool) == 'sg-aws'
