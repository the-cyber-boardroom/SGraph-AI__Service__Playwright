# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge: Schema__SG_Edge__TXT__Record
# Typed form of the _sg.<slug> routing record that OpenResty reads to find a
# backend. Wire form (under the 255-char DNS TXT limit) is key=value;key=value,
# e.g. "v=1;ip=10.0.1.5;port=8080;type=ec2;launched=1747700000;instance=i-...".
# SG_Edge__TXT__Builder converts between this schema and the wire string.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                         import Type_Safe

from sg_compute.primitives.Safe_Str__IP__Address                            import Safe_Str__IP__Address
from sg_compute.primitives.Safe_Int__Port                                   import Safe_Int__Port
from sg_compute.platforms.ec2.primitives.Safe_Str__Instance__Id             import Safe_Str__Instance__Id
from sg_compute_specs.sg_edge.enums.Enum__SG_Edge__Backend__Type            import Enum__SG_Edge__Backend__Type
from sg_compute_specs.sg_edge.primitives.Safe_Int__SG_Edge__TXT_Version     import Safe_Int__SG_Edge__TXT_Version
from sg_compute_specs.sg_edge.primitives.Safe_Int__SG_Edge__Unix_Ts         import Safe_Int__SG_Edge__Unix_Ts


class Schema__SG_Edge__TXT__Record(Type_Safe):
    version  : Safe_Int__SG_Edge__TXT_Version = Safe_Int__SG_Edge__TXT_Version()  # the `v=` field; only 1 is valid today
    ip       : Safe_Str__IP__Address          = ''                                # backend address
    port     : Safe_Int__Port                 = Safe_Int__Port()                  # backend port (e.g. 8080)
    type     : Enum__SG_Edge__Backend__Type   = Enum__SG_Edge__Backend__Type.EC2  # ec2 / fargate
    launched : Safe_Int__SG_Edge__Unix_Ts     = Safe_Int__SG_Edge__Unix_Ts()      # unix ts for staleness detection
    instance : Safe_Str__Instance__Id         = ''                                # optional — for ops, not used by proxy
