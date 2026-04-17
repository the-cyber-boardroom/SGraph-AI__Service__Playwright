# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Dict__Session__Browsers__By_Id (spec §6)
#
# Holds live Playwright Browser objects (non-serialisable). Value type is
# `object` on purpose: the schema layer is opaque to Playwright internals.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__Dict                               import Type_Safe__Dict

from sgraph_ai_service_playwright.schemas.primitives.identifiers.Session_Id                         import Session_Id


class Dict__Session__Browsers__By_Id(Type_Safe__Dict):                              # Live browser objects (not serialisable)
    expected_key_type   = Session_Id
    expected_value_type = object                                                    # Playwright Browser — opaque at schema level
