# ═══════════════════════════════════════════════════════════════════════════════
# Agent Mitmproxy — Schema__CA__Cert__Info (GET /ca/info response)
#
# Metadata about the CA cert mitmweb writes on first start. Clients fetch the
# PEM via /ca/cert and call update-ca-certificates.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                         import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text                 import Safe_Str__Text
from osbot_utils.type_safe.primitives.domains.files.safe_str.Safe_Str__File__Path            import Safe_Str__File__Path
from osbot_utils.type_safe.primitives.domains.identifiers.safe_int.Timestamp_Now             import Timestamp_Now


class Schema__CA__Cert__Info(Type_Safe):
    path               : Safe_Str__File__Path
    size_bytes         : int
    fingerprint_sha256 : Safe_Str__Text                                              # Hex, colon-separated
    not_before         : Timestamp_Now                                               # Unix ms — parsed from the PEM
    not_after          : Timestamp_Now
