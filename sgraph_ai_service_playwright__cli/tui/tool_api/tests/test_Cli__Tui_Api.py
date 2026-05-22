# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api tests: Cli__Tui_Api
# Drives the generic `tui api` Typer app (list / describe / invoke) via Typer's
# CliRunner against a registry holding the in-memory-backed S3 provider. 3.11.
# ═══════════════════════════════════════════════════════════════════════════════

import json

from typer.testing import CliRunner

from tests.unit.sgraph_ai_service_playwright__cli.aws.s3.service.S3__AWS__Client__In_Memory import S3__AWS__Client__In_Memory

from sgraph_ai_service_playwright__cli.aws.s3.tui_api.S3__Tui_Api__Provider   import S3__Tui_Api__Provider
from sgraph_ai_service_playwright__cli.tui.tool_api.cli.Cli__Tui_Api          import make_tui_api_app
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Registry import Tui_Api__Registry

runner = CliRunner()


def _app():
    client   = (S3__AWS__Client__In_Memory().add_bucket('demo-bucket')
                                            .add_object('demo-bucket', 'logs/a.txt', b'xx'))
    registry = Tui_Api__Registry().register(S3__Tui_Api__Provider(client=client))
    return make_tui_api_app(registry)


def test_list_shows_api_and_actions():
    result = runner.invoke(_app(), ['list'])
    assert result.exit_code == 0
    assert 'sg-aws.s3'   in result.stdout
    assert 'list_objects' in result.stdout


def test_describe_emits_valid_manifest_json():
    result = runner.invoke(_app(), ['describe', 'sg-aws.s3', '--json'])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data['slug'] == 'sg-aws.s3'
    assert any(action['name'] == 'list_objects' for action in data['actions'])


def test_invoke_list_objects_returns_object():
    result = runner.invoke(_app(), ['invoke', 'sg-aws.s3', 'list_objects',
                                    '--params', '{"bucket":"demo-bucket","recursive":true}'])
    assert result.exit_code == 0
    assert 'logs/a.txt' in result.stdout


def test_describe_unknown_api_exits_nonzero():
    result = runner.invoke(_app(), ['describe', 'sg-aws.nope', '--json'])
    assert result.exit_code == 1
