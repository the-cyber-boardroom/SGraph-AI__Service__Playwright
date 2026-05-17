# ═══════════════════════════════════════════════════════════════════════════════
# Waker — Schema__Endpoint__Resolution
# Result of resolving a slug to a live EC2 endpoint.
# Pure data — no methods. (No tuples — see plan delta A.8.)
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                              import Type_Safe

from sg_compute_specs.vault_publish.waker.schemas.Enum__Instance__State           import Enum__Instance__State


class Schema__Endpoint__Resolution(Type_Safe):
    slug        : str                     = ''
    instance_id : str                     = ''
    public_ip   : str                     = ''
    vault_url   : str                     = ''
    state       : Enum__Instance__State   = Enum__Instance__State.UNKNOWN
    region      : str                     = ''
