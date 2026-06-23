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
                                                                  remote_smoke_command, auth_help_lines,
                                                                  realize_secrets, apply_env_updates,
                                                                  Content_Proxy__Service,
                                                                  LOG_SOURCES, resolve_log_source,
                                                                  resolve_scripts_bucket)


class test_Cli__Content_Proxy(TestCase):

    def test_resolve_scripts_bucket_explicit_wins_else_local_env(self):
        assert resolve_scripts_bucket('my-explicit-bucket', {'CACHE__SERVICE__BUCKET_NAME': 'env-bucket'}) == 'my-explicit-bucket'
        assert resolve_scripts_bucket('',                   {'CACHE__SERVICE__BUCKET_NAME': 'env-bucket'}) == 'env-bucket'   # inherit local .env
        assert resolve_scripts_bucket('',                   {})                                            == ''             # neither set → blank (instance role / no cache bucket)

    def test_logs_command_registered(self):
        cmds = {c.name or (c.callback.__name__ if c.callback else '') for c in app.registered_commands}
        assert 'logs' in cmds

    def test_log_sources_cover_host_and_containers(self):
        assert 'boot'      in LOG_SOURCES                                            # host boot log
        assert 'cert-init' in LOG_SOURCES                                            # the TLS cert sidecar — the cert-debug source
        assert 'vault'     in LOG_SOURCES
        assert LOG_SOURCES['boot'][0].format(tail=30) == 'tail -n 30 /var/log/sg-content-proxy-boot.log'
        assert 'cp-cert-init' in LOG_SOURCES['cert-init'][0]                         # container name matches the compose container_name
        assert 'docker logs' in LOG_SOURCES['vault'][0] and 'podman logs' in LOG_SOURCES['vault'][0]

    def test_resolve_log_source_numeric_positional_is_index(self):
        keys = list(LOG_SOURCES)
        assert resolve_log_source('4', '')               == (keys[3], None)          # 'sg cp logs 4' → 4th source, stack auto-resolved
        assert resolve_log_source('still-fermi', '')      == ('', 'still-fermi')      # a real name is left as the stack
        assert resolve_log_source(None, 'vault')          == ('vault', None)          # explicit --source wins

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

    def test_auth_help_lines_show_set_cookie_and_token(self):
        lines = '\n'.join(auth_help_lines('https://localhost', 'real-token-123'))
        assert 'https://localhost/auth/set-cookie-form'    in lines                   # vault UI auth
        assert 'https://localhost/pw/auth/set-cookie-form' in lines                   # sg-playwright (/pw) auth
        assert 'real-token-123'                            in lines                   # the actual token
        assert 'x-api-key'                                 in lines                   # header alternative (canonical key name)
        assert 'placeholder' not in lines                                            # real token → no warning

    def test_auth_help_lines_flag_placeholder_token(self):
        lines = '\n'.join(auth_help_lines('https://localhost', 'change-me'))
        assert 'placeholder' in lines                                                # nudge to set a real value

    def test_realize_secrets_generates_guids_for_placeholders(self):
        env = {'FASTAPI_API_KEY_VALUE': 'change-me', 'CONTENT_PROXY__PROXYAUTH_PASS': '',
               'FAST_API__AUTH__API_KEY__VALUE': 'change-me', 'SGRAPH_SEND__ACCESS_TOKEN': 'change-me'}
        up  = realize_secrets(env)
        assert len(up['FASTAPI_API_KEY_VALUE']) == 36                                 # a uuid4 GUID
        assert up['FASTAPI_API_KEY_VALUE'] != 'change-me'
        assert up['FAST_API__AUTH__API_KEY__VALUE'] == up['SGRAPH_SEND__ACCESS_TOKEN']  # one access token, two vars
        assert up['CONTENT_PROXY__PROXYAUTH_PASS']                                    # generated too

    def test_realize_secrets_leaves_real_values_untouched(self):
        env = {'FASTAPI_API_KEY_VALUE': 'already-a-real-guid', 'CONTENT_PROXY__PROXYAUTH_PASS': 'sekret',
               'FAST_API__AUTH__API_KEY__VALUE': 'tok', 'SGRAPH_SEND__ACCESS_TOKEN': 'tok'}
        assert realize_secrets(env) == {}                                            # nothing to do

    def test_realize_secrets_aligns_access_token_pair(self):
        env = {'FAST_API__AUTH__API_KEY__VALUE': 'realtok', 'SGRAPH_SEND__ACCESS_TOKEN': 'change-me'}
        up  = realize_secrets(env)
        assert up['SGRAPH_SEND__ACCESS_TOKEN'] == 'realtok'                           # placeholder aligned to the real one, not regenerated

    def test_realize_secrets_recouples_two_divergent_reals(self):                    # the pic3 bug: both real but different → Caddy forwards SGRAPH_..., sg-playwright validates FAST_API... → 'Invalid API key value'
        env = {'FAST_API__AUTH__API_KEY__VALUE': 'old-pw-guid', 'SGRAPH_SEND__ACCESS_TOKEN': 'operator-token'}
        up  = realize_secrets(env)
        assert up['FAST_API__AUTH__API_KEY__VALUE'] == 'operator-token'              # FAST_API realigned onto the operator-facing token
        assert 'SGRAPH_SEND__ACCESS_TOKEN' not in up                                 # operator token survives unchanged (it's what `up` printed + the vault cookie uses)

    def test_apply_env_updates_rewrites_and_appends(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / '.env'
            p.write_text('# header\nFASTAPI_API_KEY_VALUE=change-me\nOTHER=keep\n')
            apply_env_updates(p, {'FASTAPI_API_KEY_VALUE': 'GUID-1', 'NEWKEY': 'v'})
            env = read_env_file(p)
            assert env['FASTAPI_API_KEY_VALUE'] == 'GUID-1'                           # rewritten in place
            assert env['OTHER'] == 'keep'                                            # untouched
            assert env['NEWKEY'] == 'v'                                              # appended
            assert '# header' in p.read_text()                                       # comments preserved

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
        env = 'FASTAPI_API_KEY_VALUE=fromfileFK\nSGRAPH_SEND__ACCESS_TOKEN=fromfileTOK\n'
        m   = _parse_env(env)
        assert m.get('FASTAPI_API_KEY_VALUE')    == 'fromfileFK'
        assert m.get('SGRAPH_SEND__ACCESS_TOKEN') == 'fromfileTOK'
        # mirror create_stack's selection logic
        import secrets
        fk  = m.get('FASTAPI_API_KEY_VALUE')     or secrets.token_urlsafe(24)
        tok = m.get('SGRAPH_SEND__ACCESS_TOKEN') or secrets.token_urlsafe(24)
        assert (fk, tok) == ('fromfileFK', 'fromfileTOK')                           # reused verbatim, not generated

    def test_missing_keys_fall_back_to_generated(self):
        from sg_compute_specs.content_proxy.service.Content_Proxy__Service import _parse_env
        m = _parse_env('SOMETHING_ELSE=1\n')
        assert m.get('FASTAPI_API_KEY_VALUE') is None                               # → create_stack generates one


class test_sg_rules(TestCase):

    def test_none_and_self_signed_open_only_caller(self):
        from sg_compute_specs.content_proxy.service.Content_Proxy__Service import sg_rules
        from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Tls import Enum__Content_Proxy__Tls
        for tls in (Enum__Content_Proxy__Tls.NONE, Enum__Content_Proxy__Tls.SELF_SIGNED):
            inbound, extra = sg_rules(tls)
            assert inbound == [8080, 443]
            assert extra == {}                                                       # no world-open ports

    def test_letsencrypt_opens_80_to_world(self):
        from sg_compute_specs.content_proxy.service.Content_Proxy__Service import sg_rules
        from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Tls import Enum__Content_Proxy__Tls
        inbound, extra = sg_rules(Enum__Content_Proxy__Tls.LETSENCRYPT)
        assert inbound == [8080, 443]
        assert extra == {80: '0.0.0.0/0'}                                           # ACME http-01 from LE servers


class test_ssm_health_probe(TestCase):

    def test_localhost_probe_command_scheme(self):
        from sg_compute_specs.content_proxy.service.Content_Proxy__Service import localhost_probe_command
        http  = localhost_probe_command(https=False)
        https = localhost_probe_command(https=True)
        assert 'http://localhost:443/' in http and '-k' not in http                 # NONE → http on host 443
        assert 'https://localhost/'    in https and '-k' in https                   # TLS → https, accept self-signed
        assert '%{http_code}' in http

    def test_parse_and_classify_codes(self):
        from sg_compute_specs.content_proxy.service.Content_Proxy__Service import parse_http_code, is_healthy_code
        assert parse_http_code('200')   == 200 and is_healthy_code(200) is True
        assert parse_http_code('404\n') == 404 and is_healthy_code(404) is True      # any non-5xx = serving
        assert parse_http_code('000')   == 0   and is_healthy_code(0)   is False     # curl couldn't connect
        assert parse_http_code('')      == 0
        assert is_healthy_code(503) is False
