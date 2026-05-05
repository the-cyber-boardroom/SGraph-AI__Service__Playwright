# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute tests — Cli__Docker (per-spec CLI)
# All tests use CliRunner — no AWS calls, no network.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from typer.testing                                                                  import CliRunner

from sg_compute_specs.docker.cli.Cli__Docker                                        import app


class test_Cli__Docker(TestCase):

    def setUp(self):
        self.runner = CliRunner()

    def test_no_args_shows_help(self):
        result = self.runner.invoke(app, ['--help'])
        assert result.exit_code == 0
        assert 'list'   in result.output
        assert 'info'   in result.output
        assert 'create' in result.output
        assert 'delete' in result.output

    def test_list_help(self):
        result = self.runner.invoke(app, ['list', '--help'])
        assert result.exit_code == 0
        assert 'region' in result.output

    def test_info_help(self):
        result = self.runner.invoke(app, ['info', '--help'])
        assert result.exit_code == 0
        assert 'stack-name' in result.output or 'STACK_NAME' in result.output

    def test_create_help(self):
        result = self.runner.invoke(app, ['create', '--help'])
        assert result.exit_code == 0
        assert 'region'        in result.output
        assert 'instance-type' in result.output
        assert 'max-hours'     in result.output
        assert 'registry'      in result.output

    def test_delete_help(self):
        result = self.runner.invoke(app, ['delete', '--help'])
        assert result.exit_code == 0
        assert 'stack-name' in result.output or 'STACK_NAME' in result.output
        assert 'yes'        in result.output
