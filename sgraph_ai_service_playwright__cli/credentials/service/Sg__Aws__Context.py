# ═══════════════════════════════════════════════════════════════════════════════
# SG Credentials — Sg__Aws__Context
# Session-level context: which role is currently active.
# Used by the REPL 'as <role>' pseudo-command and Sg__Aws__Session.
#
# Module-level singleton (_global_context) is read by Sg__Aws__Session
# via get_current_role().  The REPL sets it via set_global_role().
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

    @classmethod
    def get_current_role(cls) -> str:           # reads module-level global singleton; '' if none
        return str(_global_context.current_role)

    @classmethod
    def set_global_role(cls, role_name: str) -> None:   # REPL 'as <role>' updates global singleton
        _global_context.current_role = Safe_Str__Role__Name(role_name)

    @classmethod
    def clear_global_role(cls) -> None:         # REPL 'as' (no args) clears global singleton
        _global_context.current_role = Safe_Str__Role__Name('')


_global_context = Sg__Aws__Context()            # module-level singleton — one per process
