# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute tests — Cli__Compute__Spec per-spec dispatch
# Verifies the `sg-compute spec <spec_id> <verb>` routing works.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from typer.testing                                                                  import CliRunner

from sg_compute.cli.Cli__Compute__Spec                                              import app


class test_Cli__Compute__Spec__dispatch(TestCase):

    def setUp(self):
        self.runner = CliRunner()

    def test_spec_app_has_docker_subcommand(self):
        result = self.runner.invoke(app, ['--help'])
        assert result.exit_code == 0
        assert 'docker' in result.output

    def test_spec_docker_shows_verbs(self):
        result = self.runner.invoke(app, ['docker', '--help'])
        assert result.exit_code == 0
        assert 'list'   in result.output
        assert 'info'   in result.output
        assert 'create' in result.output
        assert 'delete' in result.output

    def test_spec_docker_list_help(self):
        result = self.runner.invoke(app, ['docker', 'list', '--help'])
        assert result.exit_code == 0
        assert 'region' in result.output

    def test_spec_docker_create_help(self):
        result = self.runner.invoke(app, ['docker', 'create', '--help'])
        assert result.exit_code == 0
        assert 'registry' in result.output

    def test_existing_list_command_still_works(self):
        result = self.runner.invoke(app, ['list'])
        assert result.exit_code == 0
        assert 'docker' in result.output

    def test_existing_info_command_still_works(self):
        result = self.runner.invoke(app, ['info', 'docker'])
        assert result.exit_code == 0
        assert 'docker' in result.output

    def test_specs_without_cli_not_mounted(self):
        result = self.runner.invoke(app, ['elastic', '--help'])
        assert result.exit_code != 0
