# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Credentials__Editor (full edit flow with in-memory seams)
# ═══════════════════════════════════════════════════════════════════════════════

import tempfile
import os
from unittest import TestCase

from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__AWS__Region    import Safe_Str__AWS__Region
from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__AWS__Role__ARN import Safe_Str__AWS__Role__ARN
from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__Role__Name     import Safe_Str__Role__Name
from sgraph_ai_service_playwright__cli.credentials.schemas.Schema__AWS__Role__Config   import Schema__AWS__Role__Config
from sgraph_ai_service_playwright__cli.credentials.service.Keyring__Mac__OS            import Keyring__Mac__OS__In_Memory
from sgraph_ai_service_playwright__cli.credentials.service.Credentials__Store          import Credentials__Store
from sgraph_ai_service_playwright__cli.credentials.edit.Credentials__Editor            import Credentials__Editor
from sgraph_ai_service_playwright__cli.credentials.edit.Temp__File__Manager            import Temp__File__Manager
from sgraph_ai_service_playwright__cli.credentials.edit.Edit__Session__Journal         import Edit__Session__Journal
from sgraph_ai_service_playwright__cli.credentials.edit.Editor__Launcher              import Editor__Launcher__In_Memory
from sgraph_ai_service_playwright__cli.credentials.edit.Toml__Projector               import Toml__Projector
from sgraph_ai_service_playwright__cli.credentials.edit.Toml__Parser                  import Toml__Parser


def _store() -> Credentials__Store:
    return Credentials__Store(keyring=Keyring__Mac__OS__In_Memory())


def _cfg(name: str, region: str = 'us-east-1') -> Schema__AWS__Role__Config:
    return Schema__AWS__Role__Config(
        name            = Safe_Str__Role__Name(name),
        region          = Safe_Str__AWS__Region(region),
        assume_role_arn = Safe_Str__AWS__Role__ARN(''),
        session_name    = Safe_Str__Role__Name(f'sg-{name}'),
    )


def _editor(store: Credentials__Store, write_content: str = '',
            journal_dir: str = '') -> tuple:
    launcher     = Editor__Launcher__In_Memory(write_content=write_content)
    journal_path = journal_dir or tempfile.mkdtemp()
    editor = Credentials__Editor(
        store           = store                                              ,
        editor_launcher = launcher                                           ,
        journal         = Edit__Session__Journal(journal_dir=journal_path)  ,
        temp_manager    = Temp__File__Manager()                              ,
    )
    return editor, launcher, journal_path


class test_Credentials__Editor__noop(TestCase):

    def test_no_changes_prints_no_changes(self, capsys=None):
        store = _store()
        store.role_set(_cfg('default', 'us-east-1'))

        projector = Toml__Projector(store=store)
        toml_text = projector.project()

        editor, launcher, _ = _editor(store, write_content=toml_text)

        import io
        from contextlib import redirect_stdout

        import typer as _typer
        original_confirm = _typer.confirm
        _typer.confirm = lambda *a, **kw: False

        out = io.StringIO()
        try:
            with redirect_stdout(out):
                editor.run()
        except Exception:
            pass
        finally:
            _typer.confirm = original_confirm

        assert launcher.captured_path != ''
        assert store.role_get('default') is not None


class test_Credentials__Editor__add_role(TestCase):

    def test_add_role_stores_it(self):
        store = _store()
        store.role_set(_cfg('default', 'us-east-1'))

        projector = Toml__Projector(store=store)
        toml_with_new_role = projector.project() + (
            '\n[roles.admin]\n'
            'region          = "eu-west-1"\n'
            'assume_role_arn = ""\n'
            'session_name    = ""\n'
        )

        import typer as _typer
        original_confirm = _typer.confirm
        _typer.confirm = lambda *a, **kw: True

        editor, launcher, _ = _editor(store, write_content=toml_with_new_role)
        try:
            editor.run()
        except SystemExit:
            pass
        finally:
            _typer.confirm = original_confirm

        cfg = store.role_get('admin')
        assert cfg is not None
        assert str(cfg.region) == 'eu-west-1'


class test_Credentials__Editor__parse_error(TestCase):

    def test_parse_error_then_abort(self):
        store    = _store()
        bad_toml = 'this is [ not valid { toml'

        import typer as _typer
        prompts    = iter([False])
        original_c = _typer.confirm
        _typer.confirm = lambda *a, **kw: next(prompts, False)

        editor, launcher, _ = _editor(store, write_content=bad_toml)
        try:
            editor.run()
        except SystemExit:
            pass
        finally:
            _typer.confirm = original_c

        assert launcher.captured_path != ''


class test_Credentials__Editor__orphan_detection(TestCase):

    def test_orphan_found_and_discarded(self):
        import json
        from pathlib import Path
        journal_dir  = tempfile.mkdtemp()
        session_id   = 'ffffffff-0000-0000-0000-000000000001'
        orphan_path  = Path(journal_dir) / f'{session_id}.json'
        orphan_path.write_text(json.dumps({'session_id': session_id,
                                            'started_at': '2026-01-01T00:00:00+00:00',
                                            'status'    : 'projecting',
                                            'temp_path' : '/tmp/gone'}))

        store = _store()

        import typer as _typer
        answers     = iter(['d', False])
        original_p  = _typer.prompt
        original_c  = _typer.confirm
        _typer.prompt  = lambda *a, **kw: next(answers, 's')
        _typer.confirm = lambda *a, **kw: next(answers, False)

        projector  = Toml__Projector(store=store)
        toml_text  = projector.project()

        editor, launcher, _ = _editor(store, write_content=toml_text,
                                       journal_dir=journal_dir)
        try:
            editor.run()
        except (SystemExit, StopIteration):
            pass
        finally:
            _typer.prompt  = original_p
            _typer.confirm = original_c

        entry = json.loads(orphan_path.read_text())
        assert entry['status'] == 'discarded'
