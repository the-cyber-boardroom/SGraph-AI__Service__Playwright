# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Cli__Credentials wipe command
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


def _cfg(name: str, region: str = 'us-east-1') -> Schema__AWS__Role__Config:
    return Schema__AWS__Role__Config(
        name            = Safe_Str__Role__Name(name),
        region          = Safe_Str__AWS__Region(region),
        assume_role_arn = Safe_Str__AWS__Role__ARN(''),
        session_name    = Safe_Str__Role__Name(f'sg-{name}'),
    )


class test_Cli__Credentials__wipe(TestCase):

    def setUp(self):
        self._store_obj = Credentials__Store(keyring=Keyring__Mac__OS__In_Memory())
        self._store_obj.role_set(_cfg('default', 'us-east-1'))
        self._store_obj.aws_credentials_set('default', 'AKIA...', 'secret')
        _cli_mod._store = lambda: self._store_obj

    def tearDown(self):
        _cli_mod._store = lambda: Credentials__Store(keyring=Keyring__Mac__OS__In_Memory())

    def test_wipe_without_flag_exits_1(self):
        runner = CliRunner()
        result = runner.invoke(app, ['wipe'])
        assert result.exit_code == 1
        assert '--yes-i-really-mean-it' in result.output

    def test_wipe_with_flag_deletes_all_sg_entries(self):
        runner = CliRunner()
        result = runner.invoke(app, ['wipe', '--yes-i-really-mean-it'])
        assert result.exit_code == 0
        assert 'Deleted' in result.output
        assert self._store_obj.role_list()               == []
        assert self._store_obj.aws_credentials_get('default') is None
