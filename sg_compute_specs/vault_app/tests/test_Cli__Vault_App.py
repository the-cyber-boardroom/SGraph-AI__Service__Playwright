# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Cli__Vault_App (typer CLI surface)
# Verifies the Builder-emitted shape + spec extras without touching AWS.
# ═══════════════════════════════════════════════════════════════════════════════

from io import StringIO

from rich.console import Console
from typer.testing import CliRunner

from sg_compute_specs.vault_app.cli.Cli__Vault_App    import (app                       ,
                                                              _render_vault_app_info    ,
                                                              _render_vault_app_create  )
from sg_compute_specs.vault_app.schemas.Schema__Vault_App__Info             import Schema__Vault_App__Info
from sg_compute_specs.vault_app.schemas.Schema__Vault_App__Create__Response import Schema__Vault_App__Create__Response


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
        assert '--access-token'    in result.output
        assert '--name'            in result.output

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

    def test_render_vault_app_info_shows_set_cookie_form(self):
        info = Schema__Vault_App__Info(stack_name='s', instance_id='i-1', state='running',
                                       public_ip='1.2.3.4', vault_url='http://1.2.3.4:8080')
        buf = StringIO()
        _render_vault_app_info(info, Console(file=buf, highlight=False, no_color=True))
        out = buf.getvalue()
        assert 'http://1.2.3.4:8080/auth/set-cookie-form' in out
        assert 'x-sgraph-access-token=YOUR_TOKEN'         in out
        assert 'location.reload()'                        in out

    def test_render_vault_app_create_shows_access_token(self):
        resp = Schema__Vault_App__Create__Response(
            stack_info   = Schema__Vault_App__Info(stack_name='zen-curie',
                                                   instance_id='i-abc',
                                                   state='pending'),
            access_token = 'super-secret-token-xyz',
            elapsed_ms   = 3800,
        )
        buf = StringIO()
        _render_vault_app_create(resp, Console(file=buf, highlight=False, no_color=True))
        out = buf.getvalue()
        assert 'super-secret-token-xyz' in out
        assert 'shown once'             in out
        # pending instance has no public IP yet — points the user at `info`
        assert 'sp vault-app info'      in out

    def test_render_vault_app_create_shows_urls_when_ip_known(self):
        resp = Schema__Vault_App__Create__Response(
            stack_info   = Schema__Vault_App__Info(stack_name='zen-curie',
                                                   instance_id='i-abc',
                                                   state='running',
                                                   public_ip='9.8.7.6',
                                                   vault_url='http://9.8.7.6:8080'),
            access_token = 'tok',
        )
        buf = StringIO()
        _render_vault_app_create(resp, Console(file=buf, highlight=False, no_color=True))
        out = buf.getvalue()
        assert 'http://9.8.7.6:8080'                       in out
        assert 'http://9.8.7.6:8080/auth/set-cookie-form'   in out

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

    def test_cert_subcommand_exists(self):
        result = runner.invoke(app, ['cert', '--help'])
        assert result.exit_code == 0
        for verb in ('generate', 'inspect', 'show', 'check'):
            assert verb in result.output

    def test_cert_generate_and_inspect_roundtrip(self, tmp_path):
        cert_path = str(tmp_path / 'cert.pem')
        key_path  = str(tmp_path / 'key.pem')
        gen = runner.invoke(app, ['cert', 'generate', '--cn', '7.7.7.7',
                                  '--out-cert', cert_path, '--out-key', key_path])
        assert gen.exit_code == 0, gen.output
        assert 'self-signed cert written' in gen.output
        inspect = runner.invoke(app, ['cert', 'inspect', '--file', cert_path])
        assert inspect.exit_code == 0
        assert 'CN=7.7.7.7' in inspect.output
        assert 'self-signed' in inspect.output

    def test_cert_inspect_requires_a_source(self):
        result = runner.invoke(app, ['cert', 'inspect'])
        assert result.exit_code != 0

    def test_create_has_with_tls_check_flag(self):
        result = runner.invoke(app, ['create', '--help'])
        assert result.exit_code == 0
        assert '--with-tls-check' in result.output

    def test_open_help_lists_known_targets(self):
        result = runner.invoke(app, ['open', '--help'])
        assert result.exit_code == 0
        assert 'host-plane' in result.output
        assert 'mitmweb'    in result.output

    def test_open_with_no_target_lists_available(self):
        result = runner.invoke(app, ['open'])
        assert result.exit_code == 0
        assert 'host-plane' in result.output
        assert 'mitmweb'    in result.output

    def test_open_rejects_unknown_target(self):
        result = runner.invoke(app, ['open', 'bogus'])
        assert result.exit_code != 0

    def test_recreate_help_documents_what_is_preserved(self):
        result = runner.invoke(app, ['recreate', '--help'])
        assert result.exit_code == 0
        assert '--with-playwright' in result.output
        assert '--with-tls-check'  in result.output
        assert '--yes'             in result.output
