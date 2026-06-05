# ═══════════════════════════════════════════════════════════════════════════════
# Tests — --interceptor-env-file / --interceptor-env wiring
# env vars reach the agent-mitmproxy container via a host-written active.env that
# compose mounts as env_file. Always written (empty when none) so env_file resolves.
# ═══════════════════════════════════════════════════════════════════════════════

import tempfile

import pytest

from sg_compute_specs.vault_app.cli                       import Cli__Vault_App as cli
from sg_compute_specs.vault_app.schemas.Schema__Vault_App__Create__Request  import Schema__Vault_App__Create__Request
from sg_compute_specs.vault_app.service.Vault_App__Compose__Template        import Vault_App__Compose__Template
from sg_compute_specs.vault_app.service.Vault_App__User_Data__Builder       import Vault_App__User_Data__Builder


class TestComposeEnvFile:

    def test_agent_mitmproxy_has_env_file(self):
        result = Vault_App__Compose__Template().render(with_playwright=True)
        assert 'env_file:'                                  in result
        assert '/opt/vault-app/interceptors/active.env'     in result

    def test_just_vault_has_no_env_file(self):
        result = Vault_App__Compose__Template().render(with_playwright=False)
        assert 'active.env' not in result


class TestUserDataEnvFile:

    def _render(self, **kw):
        return Vault_App__User_Data__Builder().render(stack_name='v', access_token='t',
                                                      with_playwright=True, **kw)

    def test_empty_env_file_written_by_default(self):
        script = self._render()
        assert 'cat > /opt/vault-app/interceptors/active.env' in script
        assert 'no interceptor env'                          in script        # empty placeholder body
        assert 'chmod 600 /opt/vault-app/interceptors/active.env' in script

    def test_custom_env_written(self):
        script = self._render(interceptor_env='FOO=bar\nTARGET=https://x')
        assert 'FOO=bar'             in script
        assert 'TARGET=https://x'    in script
        assert 'no interceptor env'  not in script

    def test_env_written_before_compose_up(self):
        script = self._render(interceptor_env='FOO=bar')
        assert script.index('active.env') < script.index('up -d')

    def test_just_vault_writes_no_env_file(self):
        script = Vault_App__User_Data__Builder().render(stack_name='v', access_token='t',
                                                        with_playwright=False)
        assert 'active.env' not in script


class TestCliEnvWiring:

    def test_inline_env_vars_merged(self):
        req = Schema__Vault_App__Create__Request()
        cli._set_extras(req, interceptor_env=['FOO=bar', 'BAZ=qux'])
        assert str(req.interceptor_env) == 'FOO=bar\nBAZ=qux'

    def test_env_file_read(self):
        with tempfile.NamedTemporaryFile('w', suffix='.env', delete=False) as f:
            f.write('A=1\nB=2\n'); path = f.name
        req = Schema__Vault_App__Create__Request()
        cli._set_extras(req, interceptor_env_file=path)
        assert str(req.interceptor_env) == 'A=1\nB=2'

    def test_file_plus_inline_merged(self):
        with tempfile.NamedTemporaryFile('w', suffix='.env', delete=False) as f:
            f.write('A=1\n'); path = f.name
        req = Schema__Vault_App__Create__Request()
        cli._set_extras(req, interceptor_env_file=path, interceptor_env=['B=2'])
        assert str(req.interceptor_env) == 'A=1\nB=2'

    def test_inline_without_equals_raises(self):
        req = Schema__Vault_App__Create__Request()
        with pytest.raises(Exception, match='KEY=VALUE'):
            cli._set_extras(req, interceptor_env=['NOTKV'])

    def test_missing_env_file_raises(self):
        req = Schema__Vault_App__Create__Request()
        with pytest.raises(Exception, match='not found'):
            cli._set_extras(req, interceptor_env_file='/no/such/file.env')

    def test_default_is_empty(self):
        assert str(Schema__Vault_App__Create__Request().interceptor_env) == ''
