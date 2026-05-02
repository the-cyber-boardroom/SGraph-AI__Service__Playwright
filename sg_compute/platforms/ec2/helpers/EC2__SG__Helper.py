# ═══════════════════════════════════════════════════════════════════════════════
# Ephemeral EC2 — EC2__SG__Helper
# Creates or reuses a per-stack security group.
# inbound_ports: opened from caller_ip/32
# extra_cidrs:   {port: cidr} for internal rules (e.g. Ollama private access)
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                         import List

import boto3                                                                        # EXCEPTION — narrow boto3 boundary

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute.platforms.ec2.helpers.EC2__Tags__Builder                                   import TAG_PURPOSE_KEY, TAG_PURPOSE_VALUE
from sg_compute.platforms.ec2.helpers.Stack__Naming                                        import Stack__Naming


class EC2__SG__Helper(Type_Safe):
    naming : Stack__Naming = None

    def setup(self, naming: Stack__Naming) -> 'EC2__SG__Helper':
        self.naming = naming
        return self

    def ec2_client(self, region: str):
        return boto3.client('ec2', region_name=region)

    def ensure_security_group(self, region        : str       ,
                                     stack_name   : str       ,
                                     caller_ip    : str       ,
                                     inbound_ports: List[int] = None,
                                     extra_cidrs  : dict      = None) -> str:
        ec2     = self.ec2_client(region)
        sg_name = self.naming.sg_name_for_stack(stack_name)

        if not caller_ip:
            raise ValueError(f'caller_ip is required to build SG rules for stack {stack_name!r}; '
                             f'auto-detection failed — pass --caller-ip explicitly')
        cidr    = f'{caller_ip}/32'

        existing = ec2.describe_security_groups(
            Filters=[{'Name': 'group-name', 'Values': [sg_name]}]
        ).get('SecurityGroups', [])

        if existing:
            sg_id = existing[0].get('GroupId', '')
        else:
            resp  = ec2.create_security_group(
                GroupName         = sg_name,
                Description       = f'ephemeral-ec2 stack: {stack_name}',
                TagSpecifications = [{'ResourceType': 'security-group',
                                      'Tags': [{'Key': TAG_PURPOSE_KEY,
                                                'Value': TAG_PURPOSE_VALUE}]}])
            sg_id = resp.get('GroupId', '')

        for port in (inbound_ports or []):
            self._authorize(ec2, sg_id, port, cidr, f'caller /32 port {port}')

        for port, extra_cidr in (extra_cidrs or {}).items():
            self._authorize(ec2, sg_id, port, extra_cidr, f'internal port {port}')

        return sg_id

    def delete_security_group(self, region: str, sg_id: str) -> bool:
        try:
            self.ec2_client(region).delete_security_group(GroupId=sg_id)
            return True
        except Exception:
            return False

    def _authorize(self, ec2, sg_id: str, port: int, cidr: str, desc: str) -> None:
        try:
            ec2.authorize_security_group_ingress(
                GroupId       = sg_id,
                IpPermissions = [{'IpProtocol': 'tcp'  ,
                                  'FromPort'  : port   ,
                                  'ToPort'    : port   ,
                                  'IpRanges'  : [{'CidrIp': cidr, 'Description': desc}]}])
        except Exception as exc:
            if 'InvalidPermission.Duplicate' not in str(exc):
                raise
