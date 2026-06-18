# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: List__Schema__Content_Proxy__Vault__Source
# Typed collection — pure type definition, no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List               import Type_Safe__List

from sg_compute_specs.content_proxy.schemas.Schema__Content_Proxy__Vault__Source    import Schema__Content_Proxy__Vault__Source


class List__Schema__Content_Proxy__Vault__Source(Type_Safe__List):
    expected_type = Schema__Content_Proxy__Vault__Source
