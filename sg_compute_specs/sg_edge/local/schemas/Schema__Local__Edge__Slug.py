# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge local: Schema__Local__Edge__Slug
# A registered slug's view: whether its A (registration) and TXT (backend) records
# exist, and where the backend points. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Local__Edge__Slug(Type_Safe):
    slug         : str
    fqdn         : str
    has_a        : bool = False                                                      # <slug>.<parent> A — "this slug is registered"
    has_txt      : bool = False                                                      # _sg.<slug>.<parent> TXT — "this slug has a live backend"
    backend_ip   : str
    backend_port : int  = 0
