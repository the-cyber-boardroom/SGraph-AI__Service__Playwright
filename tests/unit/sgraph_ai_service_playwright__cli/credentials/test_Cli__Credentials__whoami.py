# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Cli__Credentials whoami command
# ═══════════════════════════════════════════════════════════════════════════════

import os
from unittest import TestCase

from typer.testing import CliRunner

from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__AWS__Region    import Safe_Str__AWS__Region
from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__AWS__Role__ARN import Safe_Str__AWS__Role__ARN
from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__Role__Name     import Safe_Str__Role__Name
from sgraph_ai_service_playwright__cli.credentials.schemas.Schema__AWS__Role__Config   import Schema__AWS__Role__Config
from sgraph_ai_service_playwright__cli.credentials.service.Keyring__Mac__OS            import Keyring__Mac__OS__In_Memory
from sgraph_ai_service_playwright__cli.credentials.service.Credentials__Store          import Credentials__Store
from sgraph_ai_service_playwright__cli.credentials.cli.Cli__Credentials                import app, _CURRENT_ROLE_ENV
import sgraph_ai_service_playwright__cli.credentials.cli.Cli__Credentials as _cli_mod


def _cfg(name: str, region: str = 'us-east-1') -> Schema__AWS__Role__Config:
    return Schema__AWS__Role__Config(
        name            = Safe_Str__Role__Name(name),
        region          = Safe_Str__AWS__Region(region),
        assume_role_arn = Safe_Str__AWS__Role__ARN(''),
        session_name    = Safe_Str__Role__Name(f'sg-{name}'),
    )


class test_Cli__Credentials__whoami(TestCase):

    def setUp(self):
        self._store_obj = Credentials__Store(keyring=Keyring__Mac__OS__In_Memory())
        _cli_mod._store = lambda: self._store_obj
        os.environ.pop(_CURRENT_ROLE_ENV, None)

    def tearDown(self):
        _cli_mod._store = lambda: Credentials__Store(keyring=Keyring__Mac__OS__In_Memory())
        os.environ.pop(_CURRENT_ROLE_ENV, None)

    def test_whoami_single_role_prints_it_as_default(self):
        self._store_obj.role_set(_cfg('default', 'us-east-1'))
        runner = CliRunner()
        result = runner.invoke(app, ['whoami'])
        assert result.exit_code == 0
        assert 'default' in result.output

    def test_whoami_no_roles_prints_guidance(self):
        runner = CliRunner()
        result = runner.invoke(app, ['whoami'])
        assert result.exit_code == 0
        assert 'no active role' in result.output

    def test_whoami_env_var_takes_precedence(self):
        os.environ[_CURRENT_ROLE_ENV] = 'env-role'
        self._store_obj.role_set(_cfg('default', 'us-east-1'))
        runner = CliRunner()
        result = runner.invoke(app, ['whoami'])
        assert result.exit_code == 0
        assert 'env-role' in result.output

    def test_whoami_multiple_roles_prints_guidance(self):
        self._store_obj.role_set(_cfg('default', 'us-east-1'))
        self._store_obj.role_set(_cfg('admin',   'eu-west-1'))
        runner = CliRunner()
        result = runner.invoke(app, ['whoami'])
        assert result.exit_code == 0
        assert 'no active role' in result.output
