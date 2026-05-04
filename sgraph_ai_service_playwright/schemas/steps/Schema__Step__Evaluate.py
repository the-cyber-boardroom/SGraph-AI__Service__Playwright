# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Step__Evaluate (spec §5.6)
#
# The `expression` must pass the JS__Expression__Allowlist at dispatch time
# (deny-by-default). This schema only validates shape, not policy.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright.schemas.enums.Enum__Evaluate__Return_Type                         import Enum__Evaluate__Return_Type
from sgraph_ai_service_playwright.schemas.enums.Enum__Step__Action                                  import Enum__Step__Action
from sgraph_ai_service_playwright.schemas.primitives.browser.Safe_Str__JS__Expression               import Safe_Str__JS__Expression
from sgraph_ai_service_playwright.schemas.steps.Schema__Step__Base                                  import Schema__Step__Base


class Schema__Step__Evaluate(Schema__Step__Base):                                   # Run JS expression (allowlist-gated)
    action              : Enum__Step__Action         = Enum__Step__Action.EVALUATE
    expression          : Safe_Str__JS__Expression                                  # Validated against allowlist by dispatcher
    return_type         : Enum__Evaluate__Return_Type = Enum__Evaluate__Return_Type.JSON
