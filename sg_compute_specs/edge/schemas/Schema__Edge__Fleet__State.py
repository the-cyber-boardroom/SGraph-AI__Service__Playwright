# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — edge: Schema__Edge__Fleet__State
# Contents of the single S3 boot-lock object for one edge, e.g.
# s3://sg-edge-locks/<parent>/fleet-state.json. This is the ONLY non-DNS state
# in the architecture (brief 01). The Edge Waker serialises zero -> booting ->
# active transitions with an S3 If-None-Match conditional write on this object.
# Pure data — no methods. Round-trips via .json() for the S3 body.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                         import Type_Safe

from sg_compute.platforms.ec2.primitives.Safe_Str__Instance__Id             import Safe_Str__Instance__Id
from sg_compute_specs.edge.collections.List__Safe_Str__IP__Address          import List__Safe_Str__IP__Address
from sg_compute_specs.edge.enums.Enum__Edge__Fleet__State                   import Enum__Edge__Fleet__State
from sg_compute_specs.edge.primitives.Safe_Int__Edge__Cycle_Count           import Safe_Int__Edge__Cycle_Count
from sg_compute_specs.edge.primitives.Safe_Int__Edge__Unix_Ts               import Safe_Int__Edge__Unix_Ts
from sg_compute_specs.edge.primitives.Safe_Str__Edge__Parent_Domain         import Safe_Str__Edge__Parent_Domain


class Schema__Edge__Fleet__State(Type_Safe):
    parent_domain : Safe_Str__Edge__Parent_Domain = ''                          # which edge this lock governs
    state         : Enum__Edge__Fleet__State       = Enum__Edge__Fleet__State.ZERO
    instance_id   : Safe_Str__Instance__Id         = ''                          # the proxy being booted (during BOOTING)
    proxy_ips     : List__Safe_Str__IP__Address                                  # fleet membership mirror of proxies.<parent>
    zero_streak   : Safe_Int__Edge__Cycle_Count    = Safe_Int__Edge__Cycle_Count()  # consecutive idle-checks at zero vaults
    updated_at    : Safe_Int__Edge__Unix_Ts        = Safe_Int__Edge__Unix_Ts()   # last transition timestamp
