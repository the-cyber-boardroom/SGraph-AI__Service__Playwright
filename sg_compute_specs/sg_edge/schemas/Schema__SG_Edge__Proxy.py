# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge: Schema__SG_Edge__Proxy
# A single launched edge proxy instance, as returned by the launcher seam once
# it is health-green and ready to be put into the proxies.<parent> A-record set.
# The Edge Waker stores only the IP in DNS; the instance_id is carried here so a
# later terminate can target it. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                            import Type_Safe

from sg_compute.platforms.ec2.primitives.Safe_Str__Instance__Id import Safe_Str__Instance__Id
from sg_compute.primitives.Safe_Str__IP__Address               import Safe_Str__IP__Address


class Schema__SG_Edge__Proxy(Type_Safe):
    instance_id : Safe_Str__Instance__Id = ''                                       # for terminate
    ip          : Safe_Str__IP__Address  = ''                                       # written into proxies.<parent>
