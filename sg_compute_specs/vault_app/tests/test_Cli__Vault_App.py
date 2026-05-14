# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Cli__Vault_App (typer CLI surface)
# Verifies the Builder-emitted shape + spec extras without touching AWS.
# ═══════════════════════════════════════════════════════════════════════════════

from io import StringIO

from rich.console import Console
from typer.testing import CliRunner

from sg_compute_specs.vault_app.cli.Cli__Vault_App    import app, _render_vault_app_info
from sg_compute_specs.vault_app.schemas.Schema__Vault_App__Info import Schema__Vault_App__Info


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

    def test_diag_subcommand_exists(self):
        result = runner.invoke(app, ['diag', '--help'])
        assert result.exit_code == 0
        for step in ('ec2-state', 'ssm-reachable', 'container-engine',
                     'images-pulled', 'containers-up', 'vault-http', 'boot-ok'):
            assert step in result.output

    def test_render_vault_app_info_shows_vault_url(self):
        info = Schema__Vault_App__Info(
            stack_name        = 'test-stack'          ,
            instance_id       = 'i-1234567890abcdef0' ,
            region            = 'eu-west-2'            ,
            state             = 'running'              ,
            public_ip         = '1.2.3.4'              ,
            vault_url         = 'http://1.2.3.4:8080'  ,
            with_playwright   = True                   ,
            container_engine  = 'docker'               ,
            uptime_seconds    = 300                    ,
            spot              = True                   ,
        )
        buf = StringIO()
        c   = Console(file=buf, highlight=False, no_color=True)
        _render_vault_app_info(info, c)
        out = buf.getvalue()
        assert 'http://1.2.3.4:8080' in out
        assert 'with-playwright'     in out
        assert 'docker'              in out
        assert 'spot'                in out

    def test_render_vault_app_info_just_vault_mode(self):
        info = Schema__Vault_App__Info(
            stack_name       = 'lean-hopper'           ,
            instance_id      = 'i-aaabbbccc'           ,
            state            = 'running'               ,
            with_playwright  = False                   ,
            container_engine = 'podman'                ,
        )
        buf = StringIO()
        c   = Console(file=buf, highlight=False, no_color=True)
        _render_vault_app_info(info, c)
        out = buf.getvalue()
        assert 'just-vault'    in out
        assert 'podman'        in out
        assert 'with-playwright' not in out.replace('just-vault', '')
