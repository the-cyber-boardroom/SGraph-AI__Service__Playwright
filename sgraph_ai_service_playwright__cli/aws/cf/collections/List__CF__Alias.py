# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — List__CF__Alias
# Ordered list of CNAME alias strings for a CloudFront distribution.
# Pure type definition — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List import Type_Safe__List


class List__CF__Alias(Type_Safe__List):
    expected_type = str
