# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api/core/vfs: Vfs__Tui_Api__Provider
# The first CORE tool: a TUI API over a memory_fs Storage_FS. Default backend is
# Storage_FS__Memory (ephemeral — dies with the session, decision #6); swap to
# Local_Disk / Sqlite / Zip to persist. Files-as-tool: an agent pulls only what it
# needs via vfs.read. WRITE/DESTRUCTIVE tiers mean the execution center (B3) gates
# mutations — this provider is a thin, honest mapping with no gating of its own.
#
# Imports memory_fs → Python 3.12 only. Nothing on the 3.11 path imports this module.
# ═══════════════════════════════════════════════════════════════════════════════

from memory_fs.storage_fs.providers.Storage_FS__Memory import Storage_FS__Memory

from sgraph_ai_service_playwright__cli.tui.tool_api.core.vfs.schemas.Schema__Vfs__Params__Move  import Schema__Vfs__Params__Move
from sgraph_ai_service_playwright__cli.tui.tool_api.core.vfs.schemas.Schema__Vfs__Params__Path  import Schema__Vfs__Params__Path
from sgraph_ai_service_playwright__cli.tui.tool_api.core.vfs.schemas.Schema__Vfs__Params__Write import Schema__Vfs__Params__Write
from sgraph_ai_service_playwright__cli.tui.tool_api.enums.Enum__Tui_Api__Tier               import Enum__Tui_Api__Tier
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.List__Tui_Api__Action            import List__Tui_Api__Action
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.List__Tui_Api__Tier              import List__Tui_Api__Tier
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Action          import Schema__Tui_Api__Action
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Manifest        import Schema__Tui_Api__Manifest
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Result          import Schema__Tui_Api__Result
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Scope           import Schema__Tui_Api__Scope
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Provider               import Tui_Api__Provider
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Schema__Builder         import Tui_Api__Schema__Builder

_TIERS = {'vfs.list'  : Enum__Tui_Api__Tier.READ_ONLY,  'vfs.tree' : Enum__Tui_Api__Tier.READ_ONLY,
          'vfs.read'  : Enum__Tui_Api__Tier.READ_ONLY,  'vfs.stat' : Enum__Tui_Api__Tier.READ_ONLY,
          'vfs.write' : Enum__Tui_Api__Tier.WRITE,       'vfs.mkdir': Enum__Tui_Api__Tier.WRITE,
          'vfs.move'  : Enum__Tui_Api__Tier.WRITE,       'vfs.delete': Enum__Tui_Api__Tier.DESTRUCTIVE,
          'vfs.clear' : Enum__Tui_Api__Tier.DESTRUCTIVE}


class Vfs__Tui_Api__Provider(Tui_Api__Provider):
    storage : Storage_FS__Memory                                                  # ephemeral by default; swap backend to persist
    builder : Tui_Api__Schema__Builder

    def manifest(self) -> Schema__Tui_Api__Manifest:
        actions = List__Tui_Api__Action()
        actions.append(self._action('vfs.list',  'List files under a folder.',          Schema__Vfs__Params__Path))
        actions.append(self._action('vfs.tree',  'List sub-folders and files.',         Schema__Vfs__Params__Path))
        actions.append(self._action('vfs.read',  'Read a file as UTF-8 text.',          Schema__Vfs__Params__Path))
        actions.append(self._action('vfs.stat',  'Existence + size of a path.',         Schema__Vfs__Params__Path))
        actions.append(self._action('vfs.write', 'Write UTF-8 text to a path.',         Schema__Vfs__Params__Write))
        actions.append(self._action('vfs.mkdir', 'Create a folder (writes a .keep).',   Schema__Vfs__Params__Path))
        actions.append(self._action('vfs.move',  'Move a file from src to dst.',        Schema__Vfs__Params__Move))
        actions.append(self._action('vfs.delete','Delete a file.',                      Schema__Vfs__Params__Path))
        actions.append(self._action('vfs.clear', 'Delete every file in the VFS.',       None))

        tiers = List__Tui_Api__Tier()
        for tier in (Enum__Tui_Api__Tier.READ_ONLY, Enum__Tui_Api__Tier.WRITE, Enum__Tui_Api__Tier.DESTRUCTIVE):
            tiers.append(tier)

        return Schema__Tui_Api__Manifest(slug='core.vfs', tool='core', name='Virtual File System',
                                        version='0.1.0',
                                        description='In-memory virtual file system (ephemeral); files-as-tool for agents.',
                                        tiers=tiers, actions=actions)

    def _action(self, name: str, description: str, params_cls) -> Schema__Tui_Api__Action:
        capability   = 'read' if _TIERS[name] == Enum__Tui_Api__Tier.READ_ONLY else 'write'
        input_schema = self.builder.input_schema(params_cls) if params_cls is not None else {'type': 'object', 'properties': {}}
        return Schema__Tui_Api__Action(name=name, description=description, tier=_TIERS[name],
                                      scope=Schema__Tui_Api__Scope(api='core.vfs', capability=capability),
                                      input_schema=input_schema,
                                      supports_dry_run=(_TIERS[name] != Enum__Tui_Api__Tier.READ_ONLY))

    def state(self) -> dict:
        return {'files': [str(path) for path in self.storage.files__paths()]}

    def dry_run(self, action: str, params: dict) -> dict:
        if action == 'vfs.write':
            return {'path': params.get('path'), 'would_write_bytes': len(str(params.get('content', '')).encode('utf-8'))}
        if action == 'vfs.delete':
            return {'path': params.get('path'), 'would_delete': self.storage.file__exists(str(params.get('path', '')))}
        if action == 'vfs.clear':
            return {'would_clear_files': len(self.storage.files__paths())}
        return {}

    def dispatch(self, action: str, params: dict) -> Schema__Tui_Api__Result:
        try:
            if   action == 'vfs.list':
                p = Schema__Vfs__Params__Path(**params)
                data = [str(x) for x in self.storage.folder__files__all(str(p.path))]
            elif action == 'vfs.tree':
                p = Schema__Vfs__Params__Path(**params)
                data = {'folders': [str(x) for x in self.storage.folder__folders(str(p.path))],
                        'files'  : [str(x) for x in self.storage.folder__files__all(str(p.path))]}
            elif action == 'vfs.read':
                p = Schema__Vfs__Params__Path(**params)
                data = self.storage.file__str(str(p.path))
            elif action == 'vfs.stat':
                p      = Schema__Vfs__Params__Path(**params)
                exists = self.storage.file__exists(str(p.path))
                size   = len(self.storage.file__bytes(str(p.path)) or b'') if exists else 0
                data   = {'path': str(p.path), 'exists': exists, 'size': size}
            elif action == 'vfs.write':
                p = Schema__Vfs__Params__Write(**params)
                self.storage.file__save(str(p.path), p.content.encode('utf-8'))
                data = {'path': str(p.path), 'written': True}
            elif action == 'vfs.mkdir':
                p = Schema__Vfs__Params__Path(**params)
                self.storage.file__save(str(p.path).rstrip('/') + '/.keep', b'')
                data = {'path': str(p.path), 'created': True}
            elif action == 'vfs.move':
                p    = Schema__Vfs__Params__Move(**params)
                body = self.storage.file__bytes(str(p.src)) or b''
                self.storage.file__save(str(p.dst), body)
                self.storage.file__delete(str(p.src))
                data = {'src': str(p.src), 'dst': str(p.dst), 'moved': True}
            elif action == 'vfs.delete':
                p = Schema__Vfs__Params__Path(**params)
                data = {'path': str(p.path), 'deleted': self.storage.file__delete(str(p.path))}
            elif action == 'vfs.clear':
                data = {'cleared': self.storage.clear()}
            else:
                return Schema__Tui_Api__Result(ok=False, error=f'unknown action: {action}')
        except Exception as exc:
            return Schema__Tui_Api__Result(ok=False, error=f'{type(exc).__name__}: {exc}')
        return Schema__Tui_Api__Result(ok=True, data={'result': data})
