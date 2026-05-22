# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api/core/vfs: Vfs__Doc_Tree
# Reads/writes the standard /tools/<tool>/ convention tree a tool self-populates so an
# agent can orient on demand (files-as-tool, not context). Storage-agnostic: takes the
# Storage_FS as a method argument, so this module imports no memory_fs (3.11-clean).
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Vfs__Doc_Tree(Type_Safe):
    tool : str = 'tool'

    def root(self) -> str:
        return f'tools/{self.tool}/'                                              # storage key prefix (the leading '/' is cosmetic)

    def put_skills(self, storage, markdown: str) -> bool:
        return storage.file__save(self.root() + 'skills.md', markdown.encode('utf-8'))

    def put_manifest(self, storage, slug: str, manifest_json: str) -> bool:
        return storage.file__save(self.root() + f'api/{slug}.json', manifest_json.encode('utf-8'))

    def put_state(self, storage, state_json: str) -> bool:
        return storage.file__save(self.root() + 'current-state.json', state_json.encode('utf-8'))

    def read(self, storage, rel_path: str) -> str:
        return storage.file__str(self.root() + rel_path)
