# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Podman__SG__Helper
# Per-stack security group helper for sp podman. Mirrors Linux__SG__Helper.
# No inbound rule needed for SSM. extra_ports for Podman-exposed services.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                         import List

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.podman.primitives.Safe_Str__IP__Address      import Safe_Str__IP__Address
from sgraph_ai_service_playwright__cli.podman.primitives.Safe_Str__Podman__Stack__Name import Safe_Str__Podman__Stack__Name
from sgraph_ai_service_playwright__cli.podman.service.Podman__AWS__Client           import PODMAN_NAMING, TAG_PURPOSE_KEY, TAG_PURPOSE_VALUE


class Podman__SG__Helper(Type_Safe):

    def ec2_client(self, region: str):
        from sgraph_ai_service_playwright__cli.credentials.service.Sg__Aws__Session  import Sg__Aws__Session
        from sgraph_ai_service_playwright__cli.credentials.service.Credentials__Store import Credentials__Store
        return Sg__Aws__Session(store=Credentials__Store()).boto3_client_from_context(
            service_name='ec2', region=region or '')

    def ensure_security_group(self, region       : str                           ,
                                     stack_name   : Safe_Str__Podman__Stack__Name ,
                                     caller_ip    : Safe_Str__IP__Address         ,
                                     extra_ports  : List[int] = None              ) -> str:
        ec2     = self.ec2_client(region)
        sg_name = PODMAN_NAMING.sg_name_for_stack(stack_name)
        cidr    = f'{str(caller_ip)}/32'

        existing = ec2.describe_security_groups(
            Filters=[{'Name': 'group-name', 'Values': [sg_name]}]).get('SecurityGroups', [])

        if existing:
            sg_id = existing[0].get('GroupId', '')
        else:
            created = ec2.create_security_group(
                GroupName         = sg_name                                               ,
                Description       = f'SG Podman ephemeral stack: {str(stack_name)}'      ,
                TagSpecifications = [{'ResourceType': 'security-group',
                                      'Tags': [{'Key': TAG_PURPOSE_KEY, 'Value': TAG_PURPOSE_VALUE}]}])
            sg_id = created.get('GroupId', '')

        for port in (extra_ports or []):
            try:
                ec2.authorize_security_group_ingress(
                    GroupId       = sg_id,
                    IpPermissions = [{'IpProtocol': 'tcp'                                             ,
                                      'FromPort'  : port                                              ,
                                      'ToPort'    : port                                              ,
                                      'IpRanges'  : [{'CidrIp': cidr, 'Description': f'sp-podman caller /32 port {port}'}]}])
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
