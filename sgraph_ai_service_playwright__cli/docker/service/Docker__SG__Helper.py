# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Docker__SG__Helper
# Per-stack security group helper for sp docker. Mirrors Linux__SG__Helper.
# No inbound rule needed for SSM. extra_ports for Docker-exposed services.
# PORT 9000 is always opened for the host control plane.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                         import List

import boto3                                                                        # EXCEPTION — narrow boto3 boundary

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.docker.primitives.Safe_Str__IP__Address      import Safe_Str__IP__Address
from sgraph_ai_service_playwright__cli.docker.primitives.Safe_Str__Docker__Stack__Name import Safe_Str__Docker__Stack__Name
from sgraph_ai_service_playwright__cli.docker.service.Docker__AWS__Client           import DOCKER_NAMING, TAG_PURPOSE_KEY, TAG_PURPOSE_VALUE


HOST_CONTROL_PORT = 9000                                                            # Host control plane always exposed on this port


class Docker__SG__Helper(Type_Safe):

    def ec2_client(self, region: str):
        return boto3.client('ec2', region_name=region)

    def ensure_security_group(self, region       : str                          ,
                                     stack_name   : Safe_Str__Docker__Stack__Name,
                                     caller_ip    : Safe_Str__IP__Address        ,
                                     extra_ports  : List[int] = None             ,
                                     open_to_all  : bool      = False            ) -> str:
        ec2     = self.ec2_client(region)
        sg_name = DOCKER_NAMING.sg_name_for_stack(stack_name)
        cidr    = '0.0.0.0/0' if open_to_all else f'{str(caller_ip)}/32'

        existing = ec2.describe_security_groups(
            Filters=[{'Name': 'group-name', 'Values': [sg_name]}]).get('SecurityGroups', [])

        if existing:
            sg_id = existing[0].get('GroupId', '')
        else:
            created = ec2.create_security_group(
                GroupName         = sg_name                                               ,
                Description       = f'SG Docker ephemeral stack: {str(stack_name)}'      ,
                TagSpecifications = [{'ResourceType': 'security-group',
                                      'Tags': [{'Key': TAG_PURPOSE_KEY, 'Value': TAG_PURPOSE_VALUE}]}])
            sg_id = created.get('GroupId', '')

        ports_to_open = list(extra_ports or []) + [HOST_CONTROL_PORT]               # Always open host control port
        for port in ports_to_open:
            try:
                ec2.authorize_security_group_ingress(
                    GroupId       = sg_id,
                    IpPermissions = [{'IpProtocol': 'tcp'                                            ,
                                      'FromPort'  : port                                             ,
                                      'ToPort'    : port                                             ,
                                      'IpRanges'  : [{'CidrIp': cidr, 'Description': f'sp-docker caller /32 port {port}'}]}])
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
