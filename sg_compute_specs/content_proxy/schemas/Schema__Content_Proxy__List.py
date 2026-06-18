# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: Schema__Content_Proxy__List
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                         import List

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute_specs.content_proxy.schemas.Schema__Content_Proxy__Stack__Info       import Schema__Content_Proxy__Stack__Info


class Schema__Content_Proxy__List(Type_Safe):
    region : str
    stacks : List[Schema__Content_Proxy__Stack__Info]
    total  : int = 0
