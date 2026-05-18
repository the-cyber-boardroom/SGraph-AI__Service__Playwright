# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/ec2 — Schema__EC2__SG_Rule
# A single security-group rule (ingress or egress). AWS represents each rule
# as a (protocol, port-range, source-or-destination) tuple where the source
# can be an IPv4 CIDR, IPv6 CIDR, or a referenced security group.
#
# ip_protocol values: 'tcp' / 'udp' / 'icmp' / '-1' (meaning "all protocols").
# from_port / to_port use -1 to mean N/A (matches AWS convention for ICMP /
# all-protocols rules where ports are not applicable).
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws.ec2.enums.Enum__EC2__SG_Rule_Direction import Enum__EC2__SG_Rule_Direction
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__SG_Id    import Safe_Str__EC2__SG_Id


class Schema__EC2__SG_Rule(Type_Safe):
    ip_protocol      : str  = ''                                                # 'tcp' / 'udp' / 'icmp' / '-1' — kept as plain str (AWS raw)
    from_port        : int  = -1                                                # -1 means N/A (ICMP / all-protocols)
    to_port          : int  = -1                                                # -1 means N/A (ICMP / all-protocols)
    direction        : Enum__EC2__SG_Rule_Direction = Enum__EC2__SG_Rule_Direction.INGRESS
    cidr_ipv4        : str  = ''
    cidr_ipv6        : str  = ''
    referenced_sg_id : Safe_Str__EC2__SG_Id
    description      : str  = ''
