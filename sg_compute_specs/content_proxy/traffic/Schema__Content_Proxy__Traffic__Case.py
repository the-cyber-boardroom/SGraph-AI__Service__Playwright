# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: Schema__Content_Proxy__Traffic__Case
# One labelled corpus case: a URL/fixture + the action we expect the proxy to take.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Flow__Action          import Enum__Content_Proxy__Flow__Action
from sg_compute_specs.content_proxy.primitives.Safe_Str__Content_Proxy__Ref          import Safe_Str__Content_Proxy__Ref


class Schema__Content_Proxy__Traffic__Case(Type_Safe):
    name     : Safe_Str__Text                                                        # e.g. 'pii_table'
    label    : Safe_Str__Text                                                        # human: 'should-blur'
    url      : Safe_Str__Content_Proxy__Ref                                          # fixture file or live URL
    expected : Enum__Content_Proxy__Flow__Action = Enum__Content_Proxy__Flow__Action.PASSED
