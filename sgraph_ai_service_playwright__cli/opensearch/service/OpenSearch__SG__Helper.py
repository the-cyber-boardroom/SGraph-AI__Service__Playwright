# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — OpenSearch__SG__Helper
# Per-stack security group helper for sp os. Mirrors the SG portion of
# Elastic__AWS__Client. Each call is idempotent so re-creates are safe.
#
# Single responsibility: SG existence + ingress on the Dashboards public port.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.opensearch.primitives.Safe_Str__IP__Address  import Safe_Str__IP__Address
from sgraph_ai_service_playwright__cli.opensearch.primitives.Safe_Str__OS__Stack__Name import Safe_Str__OS__Stack__Name
from sgraph_ai_service_playwright__cli.opensearch.service.OpenSearch__AWS__Client   import OS_NAMING, TAG_PURPOSE_KEY, TAG_PURPOSE_VALUE


DASHBOARDS_PORT_EXTERNAL = 443                                                      # nginx TLS; serves Dashboards at / and OS REST at /_os/*


class OpenSearch__SG__Helper(Type_Safe):

    def ec2_client(self, region: str):                                              # Single seam — tests override
        from sgraph_ai_service_playwright__cli.credentials.service.Sg__Aws__Session  import Sg__Aws__Session
        from sgraph_ai_service_playwright__cli.credentials.service.Credentials__Store import Credentials__Store
        return Sg__Aws__Session(store=Credentials__Store()).boto3_client_from_context(
            service_name='ec2', region=region or '')

    def ensure_security_group(self, region: str, stack_name: Safe_Str__OS__Stack__Name, caller_ip: Safe_Str__IP__Address) -> str:
        ec2     = self.ec2_client(region)
        sg_name = OS_NAMING.sg_name_for_stack(stack_name)                           # "{stack}-sg" — never starts with reserved 'sg-'
        cidr    = f'{str(caller_ip)}/32'

        existing = ec2.describe_security_groups(
            Filters=[{'Name': 'group-name', 'Values': [sg_name]}]).get('SecurityGroups', [])

        if existing:
            sg_id = existing[0].get('GroupId', '')
        else:
            created = ec2.create_security_group(
                GroupName        = sg_name                                       ,
                Description      = f'SG OpenSearch ephemeral stack: {str(stack_name)}',  # ASCII only — AWS rejects multi-byte GroupDescription
                TagSpecifications= [{'ResourceType': 'security-group',
                                     'Tags': [{'Key': TAG_PURPOSE_KEY, 'Value': TAG_PURPOSE_VALUE}]}])
            sg_id = created.get('GroupId', '')

        try:                                                                        # Idempotent: AWS raises InvalidPermission.Duplicate if rule already exists
            ec2.authorize_security_group_ingress(
                GroupId      = sg_id,
                IpPermissions=[{'IpProtocol': 'tcp'                                                                          ,
                                'FromPort'  : DASHBOARDS_PORT_EXTERNAL                                                       ,
                                'ToPort'    : DASHBOARDS_PORT_EXTERNAL                                                       ,
                                'IpRanges'  : [{'CidrIp': cidr, 'Description': 'sp-os caller /32'}]}])
        except Exception as exc:
            if 'InvalidPermission.Duplicate' not in str(exc):
                raise
        return sg_id

    def delete_security_group(self, region: str, security_group_id: str) -> bool:   # Best-effort — returns False when AWS refuses (e.g. instance still attached)
        try:
            self.ec2_client(region).delete_security_group(GroupId=security_group_id)
            return True
        except Exception:
            return False
