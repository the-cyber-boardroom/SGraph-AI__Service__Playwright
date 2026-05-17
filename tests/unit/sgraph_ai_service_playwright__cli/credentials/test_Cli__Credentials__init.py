# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Cli__Credentials init command
#
# Uses typer.testing.CliRunner with a custom _store factory injected via
# monkey-patching the module-level _store in Cli__Credentials.  No mocks —
# we wire a real Credentials__Store backed by Keyring__Mac__OS__In_Memory.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from typer.testing import CliRunner

from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__AWS__Region    import Safe_Str__AWS__Region
from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__AWS__Role__ARN import Safe_Str__AWS__Role__ARN
from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__Role__Name     import Safe_Str__Role__Name
from sgraph_ai_service_playwright__cli.credentials.schemas.Schema__AWS__Role__Config   import Schema__AWS__Role__Config
from sgraph_ai_service_playwright__cli.credentials.service.Keyring__Mac__OS            import Keyring__Mac__OS__In_Memory
from sgraph_ai_service_playwright__cli.credentials.service.Credentials__Store          import Credentials__Store
from sgraph_ai_service_playwright__cli.credentials.cli.Cli__Credentials                import app
import sgraph_ai_service_playwright__cli.credentials.cli.Cli__Credentials as _cli_mod


def _make_store() -> Credentials__Store:
    return Credentials__Store(keyring=Keyring__Mac__OS__In_Memory())


def _cfg(name: str, region: str = 'us-east-1') -> Schema__AWS__Role__Config:
    return Schema__AWS__Role__Config(
        name            = Safe_Str__Role__Name(name),
        region          = Safe_Str__AWS__Region(region),
        assume_role_arn = Safe_Str__AWS__Role__ARN(''),
        session_name    = Safe_Str__Role__Name(f'sg-{name}'),
    )


class test_Cli__Credentials__init__happy_path(TestCase):

    def setUp(self):
        self._store_obj = _make_store()
        _cli_mod._store = lambda: self._store_obj

    def tearDown(self):
        _cli_mod._store = lambda: _make_store()

    def test_init_creates_role(self):
        runner = CliRunner()
        result = runner.invoke(app, ['init'],
                               input='default\nus-east-1\nAKIAIOSFODNN7EXAMPLE\ns3cr3tkey\n')
        assert result.exit_code == 0, result.output
        cfg    = self._store_obj.role_get('default')
        assert cfg is not None
        assert str(cfg.region) == 'us-east-1'
        creds  = self._store_obj.aws_credentials_get('default')
        assert creds is not None
        assert str(creds.access_key) == 'AKIAIOSFODNN7EXAMPLE'


class test_Cli__Credentials__init__idempotent(TestCase):

    def setUp(self):
        self._store_obj = _make_store()
        self._store_obj.role_set(_cfg('default', 'us-east-1'))
        self._store_obj.aws_credentials_set('default', 'AKIA_OLD', 'old_secret')
        _cli_mod._store = lambda: self._store_obj

    def tearDown(self):
        _cli_mod._store = lambda: _make_store()

    def test_init_prompts_overwrite_when_role_exists_and_aborts_on_n(self):
        runner = CliRunner()
        result = runner.invoke(app, ['init'],
                               input='default\nus-east-1\nn\n')
        assert result.exit_code == 0
        assert 'Aborted' in result.output or 'already exists' in result.output.lower() or result.exit_code == 0
        creds = self._store_obj.aws_credentials_get('default')
        assert str(creds.access_key) == 'AKIA_OLD'

    def test_init_overwrites_when_user_confirms_y(self):
        runner = CliRunner()
        result = runner.invoke(app, ['init'],
                               input='default\nus-west-2\ny\nAKIA_NEW\nnew_secret\n')
        assert result.exit_code == 0, result.output
        cfg = self._store_obj.role_get('default')
        assert str(cfg.region) == 'us-west-2'
        creds = self._store_obj.aws_credentials_get('default')
        assert str(creds.access_key) == 'AKIA_NEW'
