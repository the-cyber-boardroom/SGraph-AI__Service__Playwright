# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Docker: Docker__SG__Helper
# Per-node security group helper. extra_ports for Docker-exposed services.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                         import List

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute_specs.docker.primitives.Safe_Str__IP__Address                       import Safe_Str__IP__Address
from sg_compute_specs.docker.primitives.Safe_Str__Docker__Stack__Name               import Safe_Str__Docker__Stack__Name
from sg_compute_specs.docker.service.Docker__Tags                            import DOCKER_NAMING, TAG_PURPOSE_KEY, TAG_PURPOSE_VALUE


class Docker__SG__Helper(Type_Safe):

    def ec2_client(self, region: str):                                              # Single seam — tests override
        from sgraph_ai_service_playwright__cli.credentials.service.Sg__Aws__Session  import Sg__Aws__Session
        from sgraph_ai_service_playwright__cli.credentials.service.Credentials__Store import Credentials__Store
        return Sg__Aws__Session(store=Credentials__Store()).boto3_client_from_context(
            service_name='ec2', region=region or '')

    def ensure_security_group(self, region       : str                          ,
                                     stack_name   : Safe_Str__Docker__Stack__Name,
                                     caller_ip    : Safe_Str__IP__Address        ,
                                     extra_ports  : List[int] = None             ) -> str:
        ec2     = self.ec2_client(region)
        sg_name = DOCKER_NAMING.sg_name_for_stack(stack_name)
        cidr    = f'{str(caller_ip)}/32'

        existing = ec2.describe_security_groups(
            Filters=[{'Name': 'group-name', 'Values': [sg_name]}]).get('SecurityGroups', [])

        if existing:
            sg_id = existing[0].get('GroupId', '')
        else:
            created = ec2.create_security_group(
                GroupName         = sg_name                                               ,
                Description       = f'SG Docker node: {str(stack_name)}'                 ,
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
                                      'IpRanges'  : [{'CidrIp': cidr, 'Description': f'docker caller /32 port {port}'}]}])
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
