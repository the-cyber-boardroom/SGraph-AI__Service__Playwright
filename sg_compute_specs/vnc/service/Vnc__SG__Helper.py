# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — VNC: Vnc__SG__Helper
# SG ingress on port 443 (Caddy TLS). `public=True` opens to 0.0.0.0/0
# (gated by bcrypt auth). mitmproxy :8080 stays docker-network-only.
# ═══════════════════════════════════════════════════════════════════════════════

import boto3                                                                        # EXCEPTION — narrow boto3 boundary

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute_specs.vnc.primitives.Safe_Str__IP__Address                          import Safe_Str__IP__Address
from sg_compute_specs.vnc.primitives.Safe_Str__Vnc__Stack__Name                     import Safe_Str__Vnc__Stack__Name
from sg_compute_specs.vnc.service.Vnc__AWS__Client                                  import TAG_PURPOSE_KEY, TAG_PURPOSE_VALUE, VNC_NAMING


VIEWER_PORT_EXTERNAL = 443


class Vnc__SG__Helper(Type_Safe):

    def ec2_client(self, region: str):
        return boto3.client('ec2', region_name=region)

    def ensure_security_group(self, region: str, stack_name: Safe_Str__Vnc__Stack__Name,
                                     caller_ip: Safe_Str__IP__Address, public: bool = False) -> str:
        ec2     = self.ec2_client(region)
        sg_name = VNC_NAMING.sg_name_for_stack(stack_name)
        if public:
            cidr      = '0.0.0.0/0'
            cidr_desc = 'sp-vnc public ingress (basic-auth gated)'
        else:
            cidr      = f'{str(caller_ip)}/32'
            cidr_desc = 'sp-vnc caller /32'

        existing = ec2.describe_security_groups(
            Filters=[{'Name': 'group-name', 'Values': [sg_name]}]).get('SecurityGroups', [])

        if existing:
            sg_id = existing[0].get('GroupId', '')
        else:
            created = ec2.create_security_group(
                GroupName         = sg_name                                              ,
                Description       = f'SG VNC node: {str(stack_name)}'                   ,
                TagSpecifications = [{'ResourceType': 'security-group',
                                      'Tags': [{'Key': TAG_PURPOSE_KEY, 'Value': TAG_PURPOSE_VALUE}]}])
            sg_id = created.get('GroupId', '')

        try:
            ec2.authorize_security_group_ingress(
                GroupId       = sg_id,
                IpPermissions = [{'IpProtocol': 'tcp'                                             ,
                                  'FromPort'  : VIEWER_PORT_EXTERNAL                              ,
                                  'ToPort'    : VIEWER_PORT_EXTERNAL                              ,
                                  'IpRanges'  : [{'CidrIp': cidr, 'Description': cidr_desc}]}])
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
