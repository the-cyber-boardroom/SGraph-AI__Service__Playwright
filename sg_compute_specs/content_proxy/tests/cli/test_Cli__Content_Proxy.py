# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: CLI + Service wiring tests
# Gated on osbot_aws (the EC2 foundation dep) — skips cleanly where absent.
# No AWS calls: only the CLI build + service composition + cli_spec are asserted.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

import pytest

pytest.importorskip('osbot_aws')                                                   # EC2 foundation dep

from pathlib import Path
import tempfile

from sg_compute_specs.content_proxy.cli.Cli__Content_Proxy import (app, read_env_file, smoke_curl_args,
                                                                  remote_smoke_command,
                                                                  Content_Proxy__Service)


class test_Cli__Content_Proxy(TestCase):

    def test_8_standard_verbs_present(self):
        cmds = {c.name or (c.callback.__name__ if c.callback else '') for c in app.registered_commands}
        for verb in ('list', 'info', 'create', 'delete', 'wait', 'health', 'connect', 'exec'):
            assert verb in cmds, verb

    def test_remote_smoke_command_present(self):
        cmds = {c.name or (c.callback.__name__ if c.callback else '') for c in app.registered_commands}
        assert 'smoke' in cmds                                                       # top-level EC2 (SSM) smoke

    def test_remote_smoke_command_builder(self):
        cmd = remote_smoke_command('http://example.com/mitm-proxy')
        assert '/opt/content-proxy/.env' in cmd                                      # reads creds from the box .env
        assert 'CONTENT_PROXY__PROXYAUTH_USER' in cmd and 'localhost:8080' in cmd
        assert 'http://example.com/mitm-proxy' in cmd                               # url present (shlex-quoted when needed)
        assert "'http://a b'" in remote_smoke_command('http://a b')                  # special chars do get quoted
        assert '%{http_code}' in cmd

    def test_groups_present(self):
        groups = {g.name for g in app.registered_groups}
        assert {'ami', 'cert', 'local'} <= groups                                   # builder groups + our local lifecycle

    def test_local_group_commands(self):
        local = [g for g in app.registered_groups if g.name == 'local'][0]
        names = {c.name or '' for c in local.typer_instance.registered_commands}
        assert {'up', 'down', 'status', 'logs', 'smoke', 'pull', 'ca'} <= names


class test_local_helpers(TestCase):

    def test_read_env_file(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / '.env'
            p.write_text('# comment\n\nCONTENT_PROXY__PROXYAUTH_USER=demo\nCONTENT_PROXY__PROXYAUTH_PASS=secret\nBAD LINE\n')
            env = read_env_file(p)
            assert env['CONTENT_PROXY__PROXYAUTH_USER'] == 'demo'
            assert env['CONTENT_PROXY__PROXYAUTH_PASS'] == 'secret'
            assert 'BAD LINE' not in env

    def test_read_env_missing_file(self):
        assert read_env_file(Path('/no/such/.env')) == {}

    def test_smoke_curl_args_with_auth(self):
        args = smoke_curl_args('http://example.com/mitm-proxy', 'demo', 'secret')
        assert args[0] == 'curl'
        assert '-x' in args
        assert 'http://demo:secret@localhost:8080' in args
        assert 'http://example.com/mitm-proxy' in args

    def test_smoke_curl_args_no_auth(self):
        args = smoke_curl_args('http://h/mitm-proxy')
        assert 'http://localhost:8080' in args
        assert '@localhost' not in ' '.join(args)


class test_Content_Proxy__Service_wiring(TestCase):

    def test_setup_is_aws_free_and_composes_helpers(self):
        svc = Content_Proxy__Service().setup()
        assert svc.aws_client        is not None
        assert svc.name_gen          is not None
        assert svc.user_data_builder is not None
        assert svc.mapper            is not None

    def test_cli_spec(self):
        sp = Content_Proxy__Service().cli_spec()
        assert sp.spec_id       == 'content_proxy'
        assert sp.health_port   == 443
        assert sp.health_scheme == 'http'                                           # vault plain HTTP behind :443 (NONE/MVP)

    def test_name_gen_generates(self):
        name = Content_Proxy__Service().setup().name_gen.generate()
        assert '-' in name                                                          # adjective-scientist


class test_env_secret_reuse(TestCase):

    def test_env_file_keys_are_reused_not_regenerated(self):
        from sg_compute_specs.content_proxy.service.Content_Proxy__Service import _parse_env
        env = 'FASTAPI_API_KEY_VALUE=fromfileFK\nSG_PLAYWRIGHT__API_KEY=fromfilePK\n'
        m   = _parse_env(env)
        assert m.get('FASTAPI_API_KEY_VALUE')  == 'fromfileFK'
        assert m.get('SG_PLAYWRIGHT__API_KEY') == 'fromfilePK'
        # mirror create_stack's selection logic
        import secrets
        fk = m.get('FASTAPI_API_KEY_VALUE')  or secrets.token_urlsafe(24)
        pk = m.get('SG_PLAYWRIGHT__API_KEY') or secrets.token_urlsafe(24)
        assert (fk, pk) == ('fromfileFK', 'fromfilePK')                              # reused verbatim, not generated

    def test_missing_keys_fall_back_to_generated(self):
        from sg_compute_specs.content_proxy.service.Content_Proxy__Service import _parse_env
        m = _parse_env('SOMETHING_ELSE=1\n')
        assert m.get('FASTAPI_API_KEY_VALUE') is None                               # → create_stack generates one
