# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Cli__Lab
# Typer smoke tests via CliRunner. No AWS calls, no mutations.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import os
import tempfile

from typer.testing import CliRunner

from sgraph_ai_service_playwright__cli.aws.lab.cli.Cli__Lab import lab_app

runner = CliRunner()


class Test__Cli__Lab:

    def test_1__help_shows_verbs(self):
        result = runner.invoke(lab_app, ['--help'])
        assert result.exit_code == 0
        assert 'list'    in result.output
        assert 'show'    in result.output
        assert 'run'     in result.output
        assert 'sweep'   in result.output
        assert 'account' in result.output
        assert 'ledger'  in result.output
        assert 'serve'   in result.output

    def test_2__list_returns_empty(self):
        result = runner.invoke(lab_app, ['list'])
        assert result.exit_code == 0
        assert 'no experiments' in result.output.lower() or result.output.strip() == '[]'

    def test_3__show_nonexistent_errors(self):
        result = runner.invoke(lab_app, ['show', 'nonexistent-experiment'])
        assert result.exit_code == 1
        assert 'not registered' in result.output.lower() or 'error' in result.output.lower()

    def test_4__run_nonexistent_experiment_errors_not_registered(self):
        env    = {**os.environ, 'SG_AWS__LAB__ALLOW_MUTATIONS': '1'}
        result = runner.invoke(lab_app, ['run', 'nonexistent'], env=env)
        assert result.exit_code == 1
        assert 'not registered' in result.output.lower()

    def test_5__run_without_mutation_gate_errors_gate(self):
        env    = {k: v for k, v in os.environ.items() if k != 'SG_AWS__LAB__ALLOW_MUTATIONS'}
        result = runner.invoke(lab_app, ['run', 'dummy'], env=env)
        assert result.exit_code == 1
        assert 'SG_AWS__LAB__ALLOW_MUTATIONS' in result.output

    def test_6__sweep_returns_no_resources(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = runner.invoke(lab_app, ['sweep'], env={**os.environ, 'HOME': tmp})
            assert result.exit_code == 0
            assert 'no leaked' in result.output.lower()

    def test_7__account_show_prints_table(self):
        result = runner.invoke(lab_app, ['account', 'show'])
        assert result.exit_code == 0
        assert 'Account' in result.output

    def test_8__serve_errors_not_implemented(self):
        result = runner.invoke(lab_app, ['serve'])
        assert result.exit_code == 1
        assert 'not implemented' in result.output.lower()

    def test_9__runs_diff_errors_not_implemented(self):
        result = runner.invoke(lab_app, ['runs', 'diff', 'run-a', 'run-b'])
        assert result.exit_code == 1
        assert 'not implemented' in result.output.lower()

    def test_10__runs_list_returns_no_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = runner.invoke(lab_app, ['runs', 'list'], env={**os.environ, 'HOME': tmp})
            assert result.exit_code == 0
            assert 'no runs' in result.output.lower()

    def test_11__list_json_returns_empty_array(self):
        result = runner.invoke(lab_app, ['list', '--json'])
        assert result.exit_code == 0
        data   = json.loads(result.output.strip())
        assert data == []

    def test_12__sweep_json_returns_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = runner.invoke(lab_app, ['sweep', '--json'], env={**os.environ, 'HOME': tmp})
            assert result.exit_code == 0
            data   = json.loads(result.output.strip())
            assert 'leaked'  in data
            assert 'scanned' in data
            assert data['leaked'] == 0
