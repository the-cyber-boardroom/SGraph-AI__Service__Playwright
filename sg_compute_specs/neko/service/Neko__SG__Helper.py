# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Neko: Neko__SG__Helper
# Two ingress rules:
#   - TCP 443       : Caddy TLS → Neko HTTP UI (caller /32)
#   - UDP 52000-52100 : WebRTC media stream (open to 0.0.0.0/0 — browser → EC2)
# ═══════════════════════════════════════════════════════════════════════════════

import boto3                                                                        # EXCEPTION — narrow boto3 boundary

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute_specs.neko.primitives.Safe_Str__IP__Address                         import Safe_Str__IP__Address
from sg_compute_specs.neko.primitives.Safe_Str__Neko__Stack__Name                   import Safe_Str__Neko__Stack__Name
from sg_compute_specs.neko.service.Neko__AWS__Client                                import TAG_PURPOSE_KEY, TAG_PURPOSE_VALUE, NEKO_NAMING


VIEWER_PORT     = 443
WEBRTC_UDP_FROM = 52000
WEBRTC_UDP_TO   = 52100


class Neko__SG__Helper(Type_Safe):

    def ec2_client(self, region: str):
        return boto3.client('ec2', region_name=region)

    def ensure_security_group(self, region: str, stack_name: Safe_Str__Neko__Stack__Name,
                                     caller_ip: Safe_Str__IP__Address) -> str:
        ec2     = self.ec2_client(region)
        sg_name = NEKO_NAMING.sg_name_for_stack(stack_name)
        cidr    = f'{str(caller_ip)}/32'

        existing = ec2.describe_security_groups(
            Filters=[{'Name': 'group-name', 'Values': [sg_name]}]).get('SecurityGroups', [])

        if existing:
            sg_id = existing[0].get('GroupId', '')
        else:
            created = ec2.create_security_group(
                GroupName        = sg_name                                                  ,
                Description      = f'Neko ephemeral stack: {str(stack_name)}'              ,
                TagSpecifications= [{'ResourceType': 'security-group',
                                     'Tags': [{'Key': TAG_PURPOSE_KEY, 'Value': TAG_PURPOSE_VALUE}]}])
            sg_id = created.get('GroupId', '')

        for perm in [
            {'IpProtocol': 'tcp', 'FromPort': VIEWER_PORT    , 'ToPort': VIEWER_PORT    ,
             'IpRanges': [{'CidrIp': cidr        , 'Description': 'neko caddy TLS'        }]},
            {'IpProtocol': 'udp', 'FromPort': WEBRTC_UDP_FROM, 'ToPort': WEBRTC_UDP_TO   ,
             'IpRanges': [{'CidrIp': '0.0.0.0/0' , 'Description': 'neko WebRTC media (UDP)'}]},
        ]:
            try:
                ec2.authorize_security_group_ingress(GroupId=sg_id, IpPermissions=[perm])
            except Exception as exc:
                if 'InvalidPermission.Duplicate' not in str(exc):
                    raise
        return sg_id

    def delete_security_group(self, region: str, security_group_id: str) -> bool:
        try:
            self.ec2_client(region).delete_security_group(GroupId=security_group_id)
            return True
        except Exception:
            return False
