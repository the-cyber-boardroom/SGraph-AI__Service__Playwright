# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Credentials — Credentials__Editor
#
# Orchestrates the full edit-mode flow:
#   1. Scan for orphan sessions → offer resume/discard/skip
#   2. Generate session UUID + journal entry
#   3. Create temp file, project keyring → TOML
#   4. Launch editor (blocks)
#   5. Parse TOML → retry up to 3 times on error
#   6. Diff before vs after
#   7. Print diff table + prompt for confirmation
#   8. Apply changes via Credentials__Store
#   9. Shred temp file, mark journal complete
# ═══════════════════════════════════════════════════════════════════════════════

import uuid

import typer
from rich.console import Console
from rich.table   import Table

from osbot_utils.type_safe.Type_Safe                                                       import Type_Safe

from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__AWS__Region       import Safe_Str__AWS__Region
from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__AWS__Role__ARN    import Safe_Str__AWS__Role__ARN
from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__Role__Name        import Safe_Str__Role__Name
from sgraph_ai_service_playwright__cli.credentials.schemas.Schema__AWS__Role__Config      import Schema__AWS__Role__Config
from sgraph_ai_service_playwright__cli.credentials.service.Credentials__Store             import Credentials__Store
from sgraph_ai_service_playwright__cli.credentials.edit.Temp__File__Manager               import Temp__File__Manager
from sgraph_ai_service_playwright__cli.credentials.edit.Edit__Session__Journal            import Edit__Session__Journal
from sgraph_ai_service_playwright__cli.credentials.edit.Toml__Projector                   import Toml__Projector
from sgraph_ai_service_playwright__cli.credentials.edit.Toml__Parser                      import Toml__Parser
from sgraph_ai_service_playwright__cli.credentials.edit.Edit__Diff                        import Edit__Diff
from sgraph_ai_service_playwright__cli.credentials.edit.Editor__Launcher                  import Editor__Launcher
from sgraph_ai_service_playwright__cli.credentials.edit.Schema__Edit__Snapshot            import SENTINEL


class Credentials__Editor(Type_Safe):

    store           : Credentials__Store
    editor_launcher : Editor__Launcher
    journal         : Edit__Session__Journal
    temp_manager    : Temp__File__Manager

    # ── top-level entry point ─────────────────────────────────────────────────

    def run(self) -> None:
        console = Console()
        self._handle_orphans(console)

        session_id = str(uuid.uuid4())
        temp_path  = self.temp_manager.create()
        self.journal.create(session_id, temp_path)

        projector = Toml__Projector(store=self.store)
        before    = projector.snapshot()
        toml_text = projector.project()

        with open(temp_path, 'w') as f:
            f.write(toml_text)

        # launch editor and parse; retry up to 3 times on parse error
        after = None
        for attempt in range(3):
            self.editor_launcher.launch(temp_path)
            with open(temp_path) as f:
                edited = f.read()
            parser        = Toml__Parser()
            after, err    = parser.parse(edited)
            if after is not None:
                break
            console.print(f'[red]Parse error (attempt {attempt+1}/3):[/red] {err}')
            if attempt < 2:
                try_again = typer.confirm('Re-open editor to fix?', default=True)
                if not try_again:
                    self._abort(session_id, temp_path, console)
                    return
            else:
                self._abort(session_id, temp_path, console)
                return

        differ = Edit__Diff()
        result = differ.diff(before, after)

        if not result.has_changes:
            console.print('No changes.')
            self.temp_manager.shred(temp_path)
            self.journal.update_status(session_id, 'completed')
            return

        self._print_diff(result, console)
        apply = typer.confirm('Apply these changes?', default=False)
        if not apply:
            console.print('Aborted — no changes written.')
            self.temp_manager.shred(temp_path)
            self.journal.update_status(session_id, 'discarded')
            return

        try:
            self._apply(result, before, after)
        except Exception as e:
            console.print(f'[red]Apply failed:[/red] {e}')
            console.print('[yellow]Rolling back to pre-edit state…[/yellow]')
            self._rollback(before)
        finally:
            self.temp_manager.shred(temp_path)
            self.journal.update_status(session_id, 'completed')

        console.print('[green]Changes applied.[/green]')

    # ── orphan handling ───────────────────────────────────────────────────────

    def _handle_orphans(self, console: Console) -> None:
        orphans = self.journal.find_orphans()
        for orphan in orphans:
            sid   = orphan.get('session_id', '?')
            start = orphan.get('started_at', '?')
            console.print(f'[yellow]Orphan session {sid} started at {start}[/yellow]')
            choice = typer.prompt('(r)esume / (d)iscard / (s)kip', default='s')
            if choice.lower().startswith('d'):
                self.journal.discard(sid)
            # 'r' (resume) and 's' (skip) both just proceed; resume is handled by the caller re-running

    # ── apply diff to store ───────────────────────────────────────────────────

    def _apply(self, result, before, after) -> None:
        from sgraph_ai_service_playwright__cli.credentials.edit.Schema__Edit__Diff__Item  import Schema__Edit__Diff__Item

        # deletes first
        for item in result.items:
            if item.kind == 'remove':
                self._apply_remove(item)

        # adds and modifies
        for item in result.items:
            if item.kind in ('add', 'modify'):
                self._apply_add_or_modify(item, after)

    def _apply_remove(self, item) -> None:
        ns  = item.namespace
        key = item.key
        if ns == 'roles':
            self.store.role_delete(key)
            self.store.aws_credentials_delete(key)
        elif ns == 'aws_credentials':
            self.store.aws_credentials_delete(key)
        elif ns == 'vault_keys':
            self.store.vault_key_delete(key)
        elif ns == 'secrets':
            parts = key.split('/', 1)
            if len(parts) == 2:
                self.store.secret_delete(parts[0], parts[1])

    def _apply_add_or_modify(self, item, after) -> None:
        ns  = item.namespace
        key = item.key
        if ns == 'roles':
            base = key.split('/')[0]
            cfg  = (after.roles or {}).get(base, {})
            self.store.role_set(Schema__AWS__Role__Config(
                name            = Safe_Str__Role__Name(base)                                       ,
                region          = Safe_Str__AWS__Region(cfg.get('region', 'us-east-1'))            ,
                assume_role_arn = Safe_Str__AWS__Role__ARN(cfg.get('assume_role_arn', ''))         ,
                session_name    = Safe_Str__Role__Name(cfg.get('session_name', f'sg-{base}')),
            ))
        elif ns == 'aws_credentials':
            if '/' in key:
                role      = key.split('/')[0]
                creds     = (after.aws_credentials or {}).get(role, {})
                access_key = creds.get('access_key', '')
                secret_key = creds.get('secret_key', '')
                if access_key and access_key != SENTINEL and secret_key and secret_key != SENTINEL:
                    self.store.aws_credentials_set(role, access_key, secret_key)
            else:
                creds     = (after.aws_credentials or {}).get(key, {})
                access_key = creds.get('access_key', '')
                secret_key = creds.get('secret_key', '')
                if access_key != SENTINEL and secret_key != SENTINEL:
                    self.store.aws_credentials_set(key, access_key, secret_key)
        elif ns == 'vault_keys':
            value = (after.vault_keys or {}).get(key, '')
            if value and value != SENTINEL:
                self.store.vault_key_set(key, value)
        elif ns == 'secrets':
            parts = key.split('/', 1)
            if len(parts) == 2:
                ns_name, secret_name = parts
                ns_dict = (after.secrets or {}).get(ns_name, {})
                value   = ns_dict.get(secret_name, '')
                if value and value != SENTINEL:
                    self.store.secret_set(ns_name, secret_name, value)

    def _rollback(self, before) -> None:
        for role, cfg in (before.roles or {}).items():
            self.store.role_set(Schema__AWS__Role__Config(
                name            = Safe_Str__Role__Name(role)                                        ,
                region          = Safe_Str__AWS__Region(cfg.get('region', 'us-east-1'))             ,
                assume_role_arn = Safe_Str__AWS__Role__ARN(cfg.get('assume_role_arn', ''))          ,
                session_name    = Safe_Str__Role__Name(cfg.get('session_name', f'sg-{role}')),
            ))
        for role, creds in (before.aws_credentials or {}).items():
            ak = creds.get('access_key', '')
            sk = creds.get('secret_key', '')
            if ak and sk:
                self.store.aws_credentials_set(role, ak, sk)
        for name, key in (before.vault_keys or {}).items():
            if key:
                self.store.vault_key_set(name, key)
        for ns, entries in (before.secrets or {}).items():
            for name, value in entries.items():
                if value:
                    self.store.secret_set(ns, name, value)

    def _abort(self, session_id: str, temp_path: str, console: Console) -> None:
        console.print('[red]Aborting — no changes written.[/red]')
        self.temp_manager.shred(temp_path)
        self.journal.update_status(session_id, 'discarded')

    # ── diff display ──────────────────────────────────────────────────────────

    def _print_diff(self, result, console: Console) -> None:
        table = Table(title='Pending changes', show_header=True, header_style='bold')
        table.add_column('kind',      style='cyan',   min_width=6)
        table.add_column('namespace', style='magenta')
        table.add_column('key',       style='white')
        table.add_column('old',       style='red')
        table.add_column('new',       style='green')
        for item in result.items:
            table.add_row(item.kind, item.namespace, item.key,
                          item.old_value, item.new_value)
        console.print(table)
