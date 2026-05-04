# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Plugin__Event
# Payload for core:plugin.loaded / core:plugin.skipped / core:plugin.failed
# events emitted by Plugin__Registry during discovery.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                         import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text import Safe_Str__Text

from sgraph_ai_service_playwright__cli.core.plugin.primitives.Safe_Str__Plugin__Name \
                                                                             import Safe_Str__Plugin__Name


class Schema__Plugin__Event(Type_Safe):
    name      : Safe_Str__Plugin__Name  # plugin identifier, e.g. 'vnc', 'linux'
    stability : Safe_Str__Text          # only present on loaded events
    reason    : Safe_Str__Text          # only present on skipped events
    error     : Safe_Str__Text          # only present on failed events
