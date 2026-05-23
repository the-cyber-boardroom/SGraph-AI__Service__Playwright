# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for `sg sentinel rules` CLI
# ═══════════════════════════════════════════════════════════════════════════════

import json

from unittest        import skipUnless
from typer.testing   import CliRunner

from sgraph_ai_service_playwright__cli.sentinel.cli.Cli__Sentinel__Rules            import app
from sgraph_ai_service_playwright__cli.sentinel.runtime.layer1.Sentinel__L1__Source import node_available

runner = CliRunner()


class TestList:
    def test_list_json_has_six_rules(self):
        result = runner.invoke(app, ['list', '--json'])
        assert result.exit_code == 0
        assert len(json.loads(result.output)) == 6

    def test_list_table_mentions_a_rule(self):
        result = runner.invoke(app, ['list'])
        assert result.exit_code == 0
        assert '0012' in result.output


class TestShow:
    def test_show_existing(self):
        result = runner.invoke(app, ['show', '0014', '--json'])
        assert result.exit_code == 0
        assert json.loads(result.output)['name'] == 'hidden-file-probe'

    def test_show_missing_exits_nonzero(self):
        result = runner.invoke(app, ['show', '9999'])
        assert result.exit_code == 1


@skipUnless(node_available(), 'node not available')
class TestTest:
    def test_test_json_runs_canonical_set(self):
        result = runner.invoke(app, ['test', '--json'])
        assert result.exit_code == 0
        sigs = json.loads(result.output)
        assert len(sigs) == 6
        assert sigs[1]['rule_id'] == '0012'                                          # /etc/passwd
