# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Step__Result__Evaluate (spec §5.7)
#
# Design note: `return_value: Any` is the one place `Any` survives. JS
# page.evaluate() can return arbitrary JSON; there is no typed alternative
# that covers the full range. `return_type` tells the caller what to expect.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                                         import Any

from sgraph_ai_service_playwright.schemas.enums.Enum__Evaluate__Return_Type                         import Enum__Evaluate__Return_Type
from sgraph_ai_service_playwright.schemas.results.Schema__Step__Result__Base                        import Schema__Step__Result__Base


class Schema__Step__Result__Evaluate(Schema__Step__Result__Base):                   # Result from evaluate
    return_value        : Any = None                                                # JS can return anything; caller checks type
    return_type         : Enum__Evaluate__Return_Type
