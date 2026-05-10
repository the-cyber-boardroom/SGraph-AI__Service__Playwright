# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Cli__Local_Claude (typer CLI surface)
# Mirrors test_Cli__Ollama.py — verifies the Builder-emitted shape without
# touching AWS or vLLM. Gated on the same typer import approach.
# ═══════════════════════════════════════════════════════════════════════════════

import typer
from typer.testing import CliRunner

from sg_compute_specs.local_claude.cli.Cli__Local_Claude import app


runner = CliRunner()


class TestCliLocalClaude:

    def test_help_top_level(self):
        result = runner.invoke(app, ['--help'])
        assert result.exit_code == 0
        assert 'local' in result.output.lower() or 'manage' in result.output.lower()

    def test_list_subcommand_exists(self):
        result = runner.invoke(app, ['list', '--help'])
        assert result.exit_code == 0

    def test_create_subcommand_exists(self):
        result = runner.invoke(app, ['create', '--help'])
        assert result.exit_code == 0

    def test_create_extra_options_present(self):
        result = runner.invoke(app, ['create', '--help'])
        assert result.exit_code == 0
        assert '--model'              in result.output
        assert '--served-model-name'  in result.output
        assert '--tool-parser'        in result.output
        assert '--disk-size'          in result.output
        assert '--with-claude-code'   in result.output or '--no-with-claude-code' in result.output
        assert '--with-sgit'          in result.output or '--no-with-sgit'        in result.output
        assert '--use-spot'           in result.output or '--no-use-spot'         in result.output

    def test_wait_subcommand_exists(self):
        result = runner.invoke(app, ['wait', '--help'])
        assert result.exit_code == 0

    def test_health_subcommand_exists(self):
        result = runner.invoke(app, ['health', '--help'])
        assert result.exit_code == 0

    def test_delete_subcommand_exists(self):
        result = runner.invoke(app, ['delete', '--help'])
        assert result.exit_code == 0

    def test_ami_subcommand_exists(self):
        result = runner.invoke(app, ['ami', '--help'])
        assert result.exit_code == 0

    def test_ami_bake_subcommand_exists(self):
        result = runner.invoke(app, ['ami', 'bake', '--help'])
        assert result.exit_code == 0
        assert '--wait' in result.output

    def test_ami_delete_has_ami_id_arg(self):
        result = runner.invoke(app, ['ami', 'delete', '--help'])
        assert result.exit_code == 0
        assert 'ami-id' in result.output.lower() or 'AMI_ID' in result.output

    def test_models_subcommand_exists(self):
        result = runner.invoke(app, ['models', '--help'])
        assert result.exit_code == 0

    def test_logs_subcommand_exists(self):
        result = runner.invoke(app, ['logs', '--help'])
        assert result.exit_code == 0
        assert '--tail' in result.output

    def test_claude_subcommand_exists(self):
        result = runner.invoke(app, ['claude', '--help'])
        assert result.exit_code == 0

    def test_bool_defaults_with_dual_flag(self):
        result = runner.invoke(app, ['create', '--help'])
        assert result.exit_code == 0
        # --no-with-claude-code is long enough that Rich wraps/truncates the line
        # with a unicode ellipsis; check for the suffix that survives in the output
        assert 'with-claude-code' in result.output   # --with-claude-code/--no-with-claude-c…
        assert '--no-with-sgit'   in result.output
        assert '--no-use-spot'    in result.output
