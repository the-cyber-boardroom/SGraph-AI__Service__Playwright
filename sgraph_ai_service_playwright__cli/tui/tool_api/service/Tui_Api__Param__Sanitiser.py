# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api: Tui_Api__Param__Sanitiser
# Masks secret-ish param values before they land in the audit log (mirrors the JS
# sanitiseParams). Deliberately specific hints — a bare 'key' (e.g. an S3 object key)
# is NOT a secret and is left intact.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

_SECRET_HINTS = ('secret', 'token', 'password', 'passwd', 'credential',
                 'access_key', 'secret_key', 'private_key', 'api_key')


class Tui_Api__Param__Sanitiser(Type_Safe):

    def mask(self, params: dict) -> dict:
        out = {}
        for name, value in (params or {}).items():
            lowered = str(name).lower()
            out[name] = '***' if any(hint in lowered for hint in _SECRET_HINTS) else value
        return out
