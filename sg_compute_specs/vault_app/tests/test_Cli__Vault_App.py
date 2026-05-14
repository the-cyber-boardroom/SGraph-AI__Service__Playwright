# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Cli__Vault_App (typer CLI surface)
# Verifies the Builder-emitted shape + spec extras without touching AWS.
# ═══════════════════════════════════════════════════════════════════════════════

from typer.testing import CliRunner

from sg_compute_specs.vault_app.cli.Cli__Vault_App import app


runner = CliRunner()


class TestCliVaultApp:

    def test_help_top_level(self):
        result = runner.invoke(app, ['--help'])
        assert result.exit_code == 0
        assert 'vault' in result.output.lower() or 'manage' in result.output.lower()

    def test_standard_verbs_exist(self):
        for verb in ('list', 'info', 'create', 'wait', 'health', 'connect', 'exec', 'delete'):
            result = runner.invoke(app, [verb, '--help'])
            assert result.exit_code == 0, f'{verb} --help failed'

    def test_create_extra_options_present(self):
        result = runner.invoke(app, ['create', '--help'])
        assert result.exit_code == 0
        assert '--with-playwright' in result.output
        assert '--podman'          in result.output
        assert '--no-use-spot'     in result.output
        assert '--storage-mode'    in result.output
        assert '--seed-vault-keys' in result.output
        assert '--disk-size'       in result.output
        # access-token is advanced — hidden from --help
        assert '--access-token'    not in result.output

    def test_ami_subcommand_exists(self):
        result = runner.invoke(app, ['ami', '--help'])
        assert result.exit_code == 0

    def test_ami_bake_subcommand_exists(self):
        result = runner.invoke(app, ['ami', 'bake', '--help'])
        assert result.exit_code == 0
        assert '--wait' in result.output

    def test_logs_subcommand_exists(self):
        result = runner.invoke(app, ['logs', '--help'])
        assert result.exit_code == 0
        assert '--source' in result.output
        for src in ('boot', 'cloud-init', 'journal'):
            assert src in result.output

    def test_extend_subcommand_exists(self):
        result = runner.invoke(app, ['extend', '--help'])
        assert result.exit_code == 0
        assert '--add-hours' in result.output
