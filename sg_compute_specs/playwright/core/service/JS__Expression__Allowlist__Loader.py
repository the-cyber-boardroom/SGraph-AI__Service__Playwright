# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — JS__Expression__Allowlist__Loader
#
# Builds the boot-time evaluate/wait_for.function policy from the environment.
# Deny-by-default is preserved: with NEITHER env var set, load() returns an empty
# deny-all allowlist — identical to the historical behaviour. Opening scripts is a
# deliberate, security-gated opt-in (CLAUDE.md rules 10-11):
#
#   SG_PLAYWRIGHT__JS_ALLOW_ALL      '1'/'true'/'yes'/'on' → allow_all (arbitrary JS
#                                     on /sequence + /inspect). Trusted instances ONLY.
#   SG_PLAYWRIGHT__JS_ALLOWLIST_FILE  path to a newline-delimited file of exact-match
#                                     trusted expressions; blank lines and '#' comments
#                                     are ignored. Keeps deny-by-default (only listed
#                                     strings run) — the auditable middle ground.
#
# Both may be combined; allow_all wins. A missing / unreadable allowlist file is a
# silent no-op (fails closed to whatever allow_all resolved to) — a misconfigured
# path must never accidentally OPEN scripts, and must never crash boot.
#
# See library/guides/v0.2.64__enabling-script-execution.md.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                                         import List

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe
from osbot_utils.utils.Env                                                                          import get_env

from sg_compute_specs.playwright.core.consts.env_vars                                                    import (ENV_VAR__JS_ALLOW_ALL     ,
                                                                                                               ENV_VAR__JS_ALLOWLIST_FILE)
from sg_compute_specs.playwright.core.schemas.primitives.browser.Safe_Str__JS__Expression                import Safe_Str__JS__Expression
from sg_compute_specs.playwright.core.service.JS__Expression__Allowlist                                  import JS__Expression__Allowlist


TRUE_TOKENS = ('1', 'true', 'yes', 'on')                                            # Accepted truthy spellings for the allow_all flag


class JS__Expression__Allowlist__Loader(Type_Safe):

    def env_allow_all(self) -> bool:
        value = get_env(ENV_VAR__JS_ALLOW_ALL)
        return str(value).strip().lower() in TRUE_TOKENS if value else False

    def env_allowlist_path(self) -> str:
        return get_env(ENV_VAR__JS_ALLOWLIST_FILE) or ''

    def read_expressions(self, path: str) -> List[Safe_Str__JS__Expression]:        # One expression per line; blanks + '#' comments skipped. Unreadable → [] (fails closed).
        if not path:
            return []
        try:
            with open(path, 'r') as handle:
                lines = handle.read().splitlines()
        except Exception:
            return []
        out : List[Safe_Str__JS__Expression] = []
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue
            out.append(Safe_Str__JS__Expression(stripped))
        return out

    def load(self) -> JS__Expression__Allowlist:                                    # Deny-all when neither env var is set (historical default preserved)
        return JS__Expression__Allowlist(allow_all           = self.env_allow_all()                        ,
                                         allowed_expressions = self.read_expressions(self.env_allowlist_path()))
