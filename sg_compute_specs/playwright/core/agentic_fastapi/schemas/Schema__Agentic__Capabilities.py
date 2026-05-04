# ═══════════════════════════════════════════════════════════════════════════════
# Schema__Agentic__Capabilities — GET /admin/capabilities response (v0.1.29)
#
# Wire-typed mirror of the repo-root `capabilities.json` stub. First pass
# surfaces the four fields agreed in the plan; `declared_narrowing` is empty
# until lockdown layers land in a later cycle.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                                     import List

from osbot_utils.type_safe.Type_Safe                                                            import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text                    import Safe_Str__Text
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Version                 import Safe_Str__Version


class Schema__Agentic__Capabilities(Type_Safe):
    app                : Safe_Str__Text                                             # Logical app name, e.g. 'sg-playwright'
    version            : Safe_Str__Version                                          # Matches AGENTIC_APP_VERSION
    axioms             : List[Safe_Str__Text]                                       # e.g. ['statelessness', 'least-privilege-by-declaration', 'self-description']
    declared_narrowing : List[Safe_Str__Text]                                       # Empty in v0.1.29; lockdown layers land in a later cycle
