# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute tests — Cli__Ollama
# Verifies the Builder-driven CLI surface and the 3 ollama-specific extras.
# Help-only smoke; AWS calls are not exercised.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from typer.testing import CliRunner

from sg_compute_specs.ollama.cli.Cli__Ollama import app


class test_Cli__Ollama(TestCase):

    def setUp(self):
        self.runner = CliRunner()

    def test_root_help__lists_all_eight_standard_verbs_plus_extras(self):
        result = self.runner.invoke(app, ['--help'])
        assert result.exit_code == 0
        for verb in ('list', 'info', 'create', 'wait', 'health', 'connect',
                     'exec', 'delete', 'ami', 'models', 'pull', 'claude'):
            assert verb in result.output, f'missing verb: {verb}'

    def test_ami_help__lists_subcommands(self):
        result = self.runner.invoke(app, ['ami', '--help'])
        assert result.exit_code == 0
        for sub in ('list', 'bake', 'wait', 'delete'):
            assert sub in result.output, f'missing ami subcommand: {sub}'

    def test_ami_bake_help__shows_reboot_and_wait_flags(self):
        result = self.runner.invoke(app, ['ami', 'bake', '--help'])
        assert result.exit_code == 0
        for opt in ('--name', '--reboot', '--wait', '--region'):
            assert opt in result.output, f'missing ami bake option: {opt}'

    def test_ami_delete_help__requires_ami_id(self):
        result = self.runner.invoke(app, ['ami', 'delete', '--help'])
        assert result.exit_code == 0
        assert 'AMI_ID' in result.output or 'ami_id' in result.output.lower()

    def test_create_help__shows_g5_xlarge_default(self):
        result = self.runner.invoke(app, ['create', '--help'])
        assert result.exit_code == 0
        assert 'g5.xlarge' in result.output

    def test_create_help__shows_max_hours_1(self):
        result = self.runner.invoke(app, ['create', '--help'])
        assert result.exit_code == 0
        assert '1' in result.output                                        # default max-hours

    def test_create_help__lists_all_extra_options(self):
        result = self.runner.invoke(app, ['create', '--help'])
        assert result.exit_code == 0
        # standard (visible) options
        for opt in ('--model', '--disk-size'):
            assert opt in result.output, f'missing extra option: {opt}'
        # advanced options are hidden from --help
        for opt in ('--ami-base', '--with-claude', '--expose-api'):
            assert opt not in result.output, f'advanced option should be hidden: {opt}'

    def test_create_help__model_default_is_gpt_oss_20b(self):
        result = self.runner.invoke(app, ['create', '--help'])
        assert 'gpt-oss:20b' in result.output

    def test_models_help_shown(self):
        result = self.runner.invoke(app, ['models', '--help'])
        assert result.exit_code == 0

    def test_pull_help_requires_model_name(self):
        result = self.runner.invoke(app, ['pull', '--help'])
        assert result.exit_code == 0
        assert 'model' in result.output.lower()

    def test_claude_help_shown(self):
        result = self.runner.invoke(app, ['claude', '--help'])
        assert result.exit_code == 0
