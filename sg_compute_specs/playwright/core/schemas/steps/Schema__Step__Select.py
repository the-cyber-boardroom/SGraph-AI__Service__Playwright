# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Step__Select (spec §5.6)
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                                         import List

from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text                        import Safe_Str__Text

from sg_compute_specs.playwright.core.schemas.enums.Enum__Step__Action                                  import Enum__Step__Action
from sg_compute_specs.playwright.core.schemas.primitives.browser.Safe_Str__Selector                     import Safe_Str__Selector
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Base                                  import Schema__Step__Base


class Schema__Step__Select(Schema__Step__Base):                                     # Select dropdown option(s)
    action              : Enum__Step__Action = Enum__Step__Action.SELECT
    selector            : Safe_Str__Selector
    values              : List[Safe_Str__Text]                                      # For multi-select
