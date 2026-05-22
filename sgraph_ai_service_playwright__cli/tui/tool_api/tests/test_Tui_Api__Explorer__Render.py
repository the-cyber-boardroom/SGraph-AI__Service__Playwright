# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api tests: Tui_Api__Explorer__Render
# Pure render helpers (no textual) — runs on any runtime. Uses the S3 provider over
# the in-memory client.
# ═══════════════════════════════════════════════════════════════════════════════

from tests.unit.sgraph_ai_service_playwright__cli.aws.s3.service.S3__AWS__Client__In_Memory import S3__AWS__Client__In_Memory

from sgraph_ai_service_playwright__cli.aws.s3.tui_api.S3__Tui_Api__Provider              import S3__Tui_Api__Provider
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Result      import Schema__Tui_Api__Result
from sgraph_ai_service_playwright__cli.tui.tool_api.screens.Tui_Api__Explorer__Render    import Tui_Api__Explorer__Render
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Registry            import Tui_Api__Registry


def _registry():
    client = S3__AWS__Client__In_Memory().add_bucket('demo-bucket')
    return Tui_Api__Registry().register(S3__Tui_Api__Provider(client=client))


def test_action_rows():
    rows  = Tui_Api__Explorer__Render().action_rows(_registry())
    names = [row[1] for row in rows]
    assert names == ['list_buckets', 'list_objects', 'head_object']
    assert all(row[0] == 'sg-aws.s3' for row in rows)
    assert all(row[2] == 'read_only' for row in rows)


def test_action_detail_markup_shows_schema():
    registry = _registry()
    action   = registry.get('sg-aws.s3').action('list_objects')
    markup   = Tui_Api__Explorer__Render().action_detail_markup('sg-aws.s3', action)
    assert 'list_objects' in markup and '"type": "string"' in markup


def test_result_markup_ok_and_error():
    renderer = Tui_Api__Explorer__Render()
    assert 'ok'    in renderer.result_markup(Schema__Tui_Api__Result(ok=True, data={'result': []}))
    assert 'error' in renderer.result_markup(Schema__Tui_Api__Result(ok=False, error='boom'))
