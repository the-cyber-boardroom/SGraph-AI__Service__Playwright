# ═══════════════════════════════════════════════════════════════════════════════
# Waker tests — Cli__Waker
# Smoke tests for the waker CLI verbs.  fake-event is pure Python and fully
# testable; invoke/inspect/info require AWS credentials — covered by stubs.
# ═══════════════════════════════════════════════════════════════════════════════

import json

from typer.testing import CliRunner

from sg_compute_specs.vault_publish.lambdas.waker.cli.Cli__Waker import app


class TestCli__Waker__FakeEvent:
    def test_fake_event_exits_0(self):
        runner = CliRunner()
        result = runner.invoke(app, ['fake-event', '--slug', 'sara-cv'], catch_exceptions=False)
        assert result.exit_code == 0

    def test_fake_event_output_is_valid_json(self):
        runner = CliRunner()
        result = runner.invoke(app, ['fake-event', '--slug', 'sara-cv'], catch_exceptions=False)
        event  = json.loads(result.output)
        assert isinstance(event, dict)

    def test_fake_event_version_field(self):
        runner = CliRunner()
        result = runner.invoke(app, ['fake-event', '--slug', 'bob-cv'], catch_exceptions=False)
        event  = json.loads(result.output)
        assert event['version'] == '2.0'

    def test_fake_event_host_header(self):
        runner = CliRunner()
        result = runner.invoke(app, ['fake-event', '--slug', 'alice-cv'], catch_exceptions=False)
        event  = json.loads(result.output)
        assert 'alice-cv' in event['headers']['host']

    def test_fake_event_path_default_slash(self):
        runner = CliRunner()
        result = runner.invoke(app, ['fake-event', '--slug', 'x'], catch_exceptions=False)
        event  = json.loads(result.output)
        assert event['rawPath'] == '/'

    def test_fake_event_custom_path(self):
        runner = CliRunner()
        result = runner.invoke(app, ['fake-event', '--slug', 'x', '--path', '/api/v1'],
                               catch_exceptions=False)
        event  = json.loads(result.output)
        assert event['rawPath'] == '/api/v1'

    def test_fake_event_method_default_get(self):
        runner = CliRunner()
        result = runner.invoke(app, ['fake-event', '--slug', 'x'], catch_exceptions=False)
        event  = json.loads(result.output)
        assert event['requestContext']['http']['method'] == 'GET'

    def test_fake_event_custom_method(self):
        runner = CliRunner()
        result = runner.invoke(app, ['fake-event', '--slug', 'x', '--method', 'POST'],
                               catch_exceptions=False)
        event  = json.loads(result.output)
        assert event['requestContext']['http']['method'] == 'POST'

    def test_fake_event_custom_zone(self):
        runner = CliRunner()
        result = runner.invoke(app, ['fake-event', '--slug', 'x', '--zone', 'example.com'],
                               catch_exceptions=False)
        event  = json.loads(result.output)
        assert event['headers']['host'] == 'x.example.com'

    def test_fake_event_request_id_present(self):
        runner = CliRunner()
        result = runner.invoke(app, ['fake-event', '--slug', 'x'], catch_exceptions=False)
        event  = json.loads(result.output)
        assert event['requestContext']['requestId'].startswith('fake-')

    def test_fake_event_no_slug_uses_zone_as_host(self):
        runner = CliRunner()
        result = runner.invoke(app, ['fake-event', '--zone', 'test.sg-labs.app'],
                               catch_exceptions=False)
        event  = json.loads(result.output)
        assert event['headers']['host'] == 'test.sg-labs.app'


class TestCli__Waker__Stubs:
    def test_tail_exits_0(self):
        runner = CliRunner()
        result = runner.invoke(app, ['tail'], catch_exceptions=False)
        assert result.exit_code == 0

    def test_logs_exits_0(self):
        runner = CliRunner()
        result = runner.invoke(app, ['logs'], catch_exceptions=False)
        assert result.exit_code == 0

    def test_trace_exits_0(self):
        runner = CliRunner()
        result = runner.invoke(app, ['trace'], catch_exceptions=False)
        assert result.exit_code == 0

    def test_query_exits_0(self):
        runner = CliRunner()
        result = runner.invoke(app, ['query'], catch_exceptions=False)
        assert result.exit_code == 0
