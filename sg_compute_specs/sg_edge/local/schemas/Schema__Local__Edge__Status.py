# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge local: Schema__Local__Edge__Status
# Full snapshot of the local edge: deployed?, parent zone, proxy fleet, registered
# slugs, teardown counter, and any check issues. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                       import Type_Safe

from sg_compute_specs.sg_edge.schemas.List__SG_Edge__IP                    import List__SG_Edge__IP
from sg_compute_specs.sg_edge.local.schemas.List__Local__Edge__Slug        import List__Local__Edge__Slug
from sg_compute_specs.sg_edge.local.schemas.List__Local__Edge__Issue       import List__Local__Edge__Issue


class Schema__Local__Edge__Status(Type_Safe):
    deployed     : bool = False                                                      # stack marker present
    parent       : str                                                               # the local edge zone (edge.sg-labs.local)
    zone_exists  : bool = False                                                      # hosted zone present in the local DNS file
    wildcard     : bool = False                                                      # *.<parent> A present (CloudFront equivalent)
    proxy_ips    : List__SG_Edge__IP                                                 # proxies.<parent> A values (the fleet)
    zero_streak  : int  = 0                                                          # _state.<parent> idle counter
    slugs        : List__Local__Edge__Slug                                           # registered + backed slugs
    issues       : List__Local__Edge__Issue                                          # check findings (empty on a clean check)
