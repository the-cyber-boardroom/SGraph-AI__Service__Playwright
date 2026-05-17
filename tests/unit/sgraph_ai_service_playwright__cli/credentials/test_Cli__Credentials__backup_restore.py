# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Cli__Credentials backup and restore commands
# ═══════════════════════════════════════════════════════════════════════════════

import tempfile
import os
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


class test_Cli__Credentials__backup_restore(TestCase):

    def setUp(self):
        self._tmp         = tempfile.mkdtemp()
        self._backup_path = os.path.join(self._tmp, 'backup.sg')
        self._store_obj   = Credentials__Store(keyring=Keyring__Mac__OS__In_Memory())
        self._store_obj.role_set(_cfg('default', 'us-east-1'))
        self._store_obj.aws_credentials_set('default', 'AKIAIOSFODNN7EXAMPLE', 's3cr3t')
        _cli_mod._store = lambda: self._store_obj

    def tearDown(self):
        _cli_mod._store = lambda: Credentials__Store(keyring=Keyring__Mac__OS__In_Memory())
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_backup_creates_encrypted_file(self):
        runner = CliRunner()
        result = runner.invoke(app, ['backup', '--to', self._backup_path],
                               input='passphrase123\npassphrase123\n')
        assert result.exit_code == 0, result.output
        assert os.path.exists(self._backup_path)
        assert 'sg-backup-v1' in open(self._backup_path).read()

    def test_restore_recovers_entries(self):
        runner = CliRunner()
        runner.invoke(app, ['backup', '--to', self._backup_path],
                      input='passphrase123\npassphrase123\n')
        fresh_store = Credentials__Store(keyring=Keyring__Mac__OS__In_Memory())
        _cli_mod._store = lambda: fresh_store
        result = runner.invoke(app, ['restore', '--from', self._backup_path],
                               input='passphrase123\n')
        assert result.exit_code == 0, result.output
        assert 'Restored' in result.output
        creds = fresh_store.aws_credentials_get('default')
        assert creds is not None
        assert str(creds.access_key) == 'AKIAIOSFODNN7EXAMPLE'

    def test_restore_wrong_passphrase_exits_1(self):
        runner = CliRunner()
        runner.invoke(app, ['backup', '--to', self._backup_path],
                      input='correct-passphrase\ncorrect-passphrase\n')
        result = runner.invoke(app, ['restore', '--from', self._backup_path],
                               input='wrong-passphrase\n')
        assert result.exit_code == 1
        assert 'Decryption failed' in result.output or 'failed' in result.output.lower()

    def test_restore_conflict_without_overwrite_exits_1(self):
        runner = CliRunner()
        runner.invoke(app, ['backup', '--to', self._backup_path],
                      input='pass\npass\n')
        result = runner.invoke(app, ['restore', '--from', self._backup_path],
                               input='pass\n')
        assert result.exit_code == 1
        assert 'Conflicts' in result.output or 'conflict' in result.output.lower()

    def test_restore_with_overwrite_succeeds(self):
        runner = CliRunner()
        runner.invoke(app, ['backup', '--to', self._backup_path],
                      input='pass\npass\n')
        result = runner.invoke(app, ['restore', '--from', self._backup_path, '--overwrite'],
                               input='pass\n')
        assert result.exit_code == 0, result.output
        assert 'Restored' in result.output
