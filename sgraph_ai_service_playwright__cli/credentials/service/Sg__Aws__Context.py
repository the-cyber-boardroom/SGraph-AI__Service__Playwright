# ═══════════════════════════════════════════════════════════════════════════════
# SG Credentials — Sg__Aws__Context
# Session-level context: which role is currently active.
# Used by the REPL 'as <role>' pseudo-command and Sg__Aws__Session.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                        import Type_Safe

from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__Role__Name         import Safe_Str__Role__Name


class Sg__Aws__Context(Type_Safe):
    current_role    : Safe_Str__Role__Name      # empty = no role pinned

    def set_role(self, role_name: str) -> 'Sg__Aws__Context':
        self.current_role = Safe_Str__Role__Name(role_name)
        return self

    def clear_role(self) -> 'Sg__Aws__Context':
        self.current_role = Safe_Str__Role__Name('')
        return self

    def has_role(self) -> bool:
        return bool(str(self.current_role))
