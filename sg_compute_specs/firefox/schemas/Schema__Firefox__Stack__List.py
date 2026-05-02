# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Firefox: Schema__Firefox__Stack__List
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sg_compute_specs.firefox.collections.List__Schema__Firefox__Stack__Info        import List__Schema__Firefox__Stack__Info


class Schema__Firefox__Stack__List(Type_Safe):
    region : Safe_Str__Text
    stacks : List__Schema__Firefox__Stack__Info
    total  : int = 0
