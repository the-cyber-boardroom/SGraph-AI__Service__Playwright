# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/ec2 — Schema__EC2__Route
# Single route within a Route Table.
# `gateway_id` holds the target gateway identifier — `local`, igw-…, nat-…,
# vgw-…, pcx-…, eigw-…, or '' when the route targets something else
# (e.g. NetworkInterfaceId / InstanceId / TransitGatewayId). The destination
# can be either a CIDR (IPv4) or a prefix-list — represented as a plain str
# because the prefix-list form (pl-xxxxxxxx) doesn't match the CIDR regex.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__EC2__Route(Type_Safe):
    destination_cidr : str = ''                                                 # plain str: covers CIDR + prefix-list forms returned by AWS
    gateway_id       : str = ''
    state            : str = ''
    origin           : str = ''
