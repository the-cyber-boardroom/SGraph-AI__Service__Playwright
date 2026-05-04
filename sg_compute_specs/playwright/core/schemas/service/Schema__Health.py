# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Health (GET /health response, spec §5.1)
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                              import List

from osbot_utils.type_safe.Type_Safe                                                     import Type_Safe
from osbot_utils.type_safe.primitives.domains.identifiers.safe_int.Timestamp_Now         import Timestamp_Now

from sg_compute_specs.playwright.core.schemas.service.Schema__Health__Check                  import Schema__Health__Check


class Schema__Health(Type_Safe):                                                    # GET /health response
    healthy   : bool                                                                # Aggregate of all checks
    checks    : List[Schema__Health__Check]
    timestamp : Timestamp_Now
