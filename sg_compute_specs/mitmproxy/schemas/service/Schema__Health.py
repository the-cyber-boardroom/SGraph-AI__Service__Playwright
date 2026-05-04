# ═══════════════════════════════════════════════════════════════════════════════
# Agent Mitmproxy — Schema__Health (GET /health/status response)
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                              import List

from osbot_utils.type_safe.Type_Safe                                                     import Type_Safe
from osbot_utils.type_safe.primitives.domains.identifiers.safe_int.Timestamp_Now         import Timestamp_Now

from sg_compute_specs.mitmproxy.schemas.service.Schema__Health__Check                   import Schema__Health__Check


class Schema__Health(Type_Safe):
    healthy   : bool                                                                 # Aggregate of all checks
    checks    : List[Schema__Health__Check]
    timestamp : Timestamp_Now
