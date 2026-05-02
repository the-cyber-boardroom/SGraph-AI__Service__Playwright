# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute tests — Cli__Compute__Spec
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                 import TestCase

from typer.testing                                                            import CliRunner

from sg_compute.cli.Cli__Compute__Spec                                       import app


class test_Cli__Compute__Spec(TestCase):

    def setUp(self):
        self.runner = CliRunner()

    def test_list_shows_known_specs(self):
        result = self.runner.invoke(app, ['list'])
        assert result.exit_code == 0, result.output
        assert 'docker'      in result.output
        assert 'ollama'      in result.output
        assert 'open_design' in result.output
        assert 'podman'      in result.output

    def test_list_shows_header_columns(self):
        result = self.runner.invoke(app, ['list'])
        assert result.exit_code == 0
        assert 'spec-id'      in result.output
        assert 'display-name' in result.output
        assert 'stability'    in result.output

    def test_info_known_spec(self):
        result = self.runner.invoke(app, ['info', 'docker'])
        assert result.exit_code == 0, result.output
        assert 'docker'          in result.output
        assert 'Docker'          in result.output
        assert 'version'         in result.output

    def test_info_shows_capabilities(self):
        result = self.runner.invoke(app, ['info', 'docker'])
        assert result.exit_code == 0
        assert 'caps' in result.output

    def test_info_unknown_spec_exits_nonzero(self):
        result = self.runner.invoke(app, ['info', 'no_such_spec'])
        assert result.exit_code != 0

    def test_info_unknown_spec_mentions_valid_ids(self):
        result = self.runner.invoke(app, ['info', 'no_such_spec'])
        assert 'docker' in result.output or 'registered' in result.output

    def test_no_args_shows_help(self):
        result = self.runner.invoke(app, [])
        assert 'list' in result.output
        assert 'info' in result.output
