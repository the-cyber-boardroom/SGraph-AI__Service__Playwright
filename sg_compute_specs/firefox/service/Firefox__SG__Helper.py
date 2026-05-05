# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Firefox: Firefox__SG__Helper
# One ingress rule: 443 TCP (noVNC HTTPS, forwarded to container:5800).
# mitmweb (8081) is internal-only — not exposed in the SG.
# ═══════════════════════════════════════════════════════════════════════════════

import boto3

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute_specs.firefox.service.Firefox__Tags                          import (FIREFOX_NAMING    ,
                                                                                             TAG_PURPOSE_KEY   ,
                                                                                             TAG_PURPOSE_VALUE )

VIEWER_PORT = 443


class Firefox__SG__Helper(Type_Safe):

    def ec2_client(self, region: str):
        return boto3.client('ec2', region_name=region)

    def ensure_security_group(self, region: str, stack_name: str, cidr: str) -> str:
        ec2     = self.ec2_client(region)
        sg_name = FIREFOX_NAMING.sg_name_for_stack(stack_name)

        existing = ec2.describe_security_groups(
            Filters=[{'Name': 'group-name', 'Values': [sg_name]}]).get('SecurityGroups', [])

        if existing:
            sg_id = existing[0].get('GroupId', '')
        else:
            created = ec2.create_security_group(
                GroupName        = sg_name,
                Description      = f'Firefox ephemeral stack: {str(stack_name)}',
                TagSpecifications= [{'ResourceType': 'security-group',
                                     'Tags': [{'Key': TAG_PURPOSE_KEY, 'Value': TAG_PURPOSE_VALUE}]}])
            sg_id = created.get('GroupId', '')

        try:
            ec2.authorize_security_group_ingress(GroupId=sg_id, IpPermissions=[
                {'IpProtocol': 'tcp', 'FromPort': VIEWER_PORT, 'ToPort': VIEWER_PORT,
                 'IpRanges': [{'CidrIp': cidr, 'Description': 'firefox noVNC web UI'}]}])
        except Exception as exc:
            if 'InvalidPermission.Duplicate' not in str(exc):
                raise
        return sg_id

    def delete_security_group(self, region: str, sg_id: str) -> bool:
        try:
            self.ec2_client(region).delete_security_group(GroupId=sg_id)
            return True
        except Exception:
            return False
