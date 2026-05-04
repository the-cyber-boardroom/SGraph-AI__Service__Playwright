# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — JS__Expression__Allowlist
#
# Deny-by-default gate for the EVALUATE step. The service instance starts
# with an empty `allowed_expressions` list — every `evaluate` call is rejected
# until the operator explicitly populates the allowlist at boot time (typically
# from a vault-stored config). Exact-match semantics keep the policy auditable.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                                         import List

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe

from sg_compute_specs.playwright.core.schemas.primitives.browser.Safe_Str__JS__Expression               import Safe_Str__JS__Expression


class JS__Expression__Allowlist(Type_Safe):                                         # Deny-all by default
    allowed_expressions : List[Safe_Str__JS__Expression]                            # Exact-match trusted JS strings
    allow_all           : bool = False                                              # Bypass allowlist — screenshot surface sets this (each call is an isolated session)

    def is_allowed(self, expression: Safe_Str__JS__Expression) -> bool:             # Exact-match check; allow_all bypasses for trusted callers
        if self.allow_all:
            return True
        candidate = str(expression)
        return any(str(allowed) == candidate for allowed in self.allowed_expressions)
