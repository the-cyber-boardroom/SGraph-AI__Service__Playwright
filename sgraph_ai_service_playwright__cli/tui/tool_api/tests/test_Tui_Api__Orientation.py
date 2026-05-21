# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api tests: orientation surface (B6)
# The S3 provider's orientation() + the status/whatsnew CLI commands, over the
# in-memory client. 3.11.
# ═══════════════════════════════════════════════════════════════════════════════

import json

from typer.testing import CliRunner

from tests.unit.sgraph_ai_service_playwright__cli.aws.s3.service.S3__AWS__Client__In_Memory import S3__AWS__Client__In_Memory

from sgraph_ai_service_playwright__cli.aws.s3.tui_api.S3__Tui_Api__Provider   import S3__Tui_Api__Provider
from sgraph_ai_service_playwright__cli.tui.tool_api.cli.Cli__Tui_Api          import make_tui_api_app
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Registry import Tui_Api__Registry

runner = CliRunner()


def _app():
    registry = Tui_Api__Registry().register(S3__Tui_Api__Provider(client=S3__AWS__Client__In_Memory().add_bucket('demo-bucket')))
    return make_tui_api_app(registry)


def test_s3_orientation_has_status_and_changes():
    provider    = S3__Tui_Api__Provider(client=S3__AWS__Client__In_Memory())
    orientation = provider.orientation()
    assert orientation.status['healthy'] is True
    assert len(orientation.recent_changes) >= 1
    assert str(orientation.recent_changes[0].kind) == 'feature'


def test_cli_status_shows_available_actions_and_health():
    result = runner.invoke(_app(), ['status', 'sg-aws.s3'])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data['status']['healthy'] is True
    assert 'list_buckets' in data['available_actions']
    assert len(data['recent_changes']) >= 1


def test_cli_whatsnew_renders_changes():
    result = runner.invoke(_app(), ['whatsnew', 'sg-aws.s3'])
    assert result.exit_code == 0
    assert 'Read-only S3' in result.stdout and 'feature' in result.stdout
