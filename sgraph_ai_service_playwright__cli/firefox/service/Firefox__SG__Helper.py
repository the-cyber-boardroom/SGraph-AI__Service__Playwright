# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Firefox__SG__Helper
# Per-stack security group for Firefox (jlesage/firefox noVNC web UI).
# One ingress rule:
#   443 TCP — jlesage/firefox noVNC web UI (HTTPS, forwarded to container:5800)
# mitmweb (8081) is intentionally NOT exposed — internal only.
# CIDR is caller-supplied: pass a /32 to lock to one IP, 0.0.0.0/0 for open,
# or a VPC CIDR when sitting behind an ALB.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.firefox.primitives.Safe_Str__Firefox__Stack__Name import Safe_Str__Firefox__Stack__Name
from sgraph_ai_service_playwright__cli.firefox.service.Firefox__AWS__Client         import TAG_PURPOSE_KEY, TAG_PURPOSE_VALUE, FIREFOX_NAMING


VIEWER_PORT  = 443                                                                  # HTTPS (443:5800 port-forward in docker-compose)


class Firefox__SG__Helper(Type_Safe):

    def ec2_client(self, region: str):
        from sgraph_ai_service_playwright__cli.credentials.service.Sg__Aws__Session  import Sg__Aws__Session
        from sgraph_ai_service_playwright__cli.credentials.service.Credentials__Store import Credentials__Store
        return Sg__Aws__Session(store=Credentials__Store()).boto3_client_from_context(
            service_name='ec2', region=region or '')

    def ensure_security_group(self, region: str, stack_name: Safe_Str__Firefox__Stack__Name,
                                     cidr: str) -> str:                             # cidr e.g. '1.2.3.4/32', '10.0.0.0/8', '0.0.0.0/0'
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
