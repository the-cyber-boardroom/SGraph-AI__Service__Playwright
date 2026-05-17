# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Vnc__SG__Helper
# Per-stack security group helper for sp vnc. Mirrors the SG portion of the
# OS / Prom helpers. Each call is idempotent so re-creates are safe.
#
# SG ingress on port 443 (nginx TLS — the operator-facing UI + proxied
# mitmweb). Per plan doc 6, KasmVNC port 3000 stays SSM-only (not in SG)
# and the mitmproxy proxy port 8080 is loopback-only on the docker network.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.vnc.primitives.Safe_Str__IP__Address         import Safe_Str__IP__Address
from sgraph_ai_service_playwright__cli.vnc.primitives.Safe_Str__Vnc__Stack__Name    import Safe_Str__Vnc__Stack__Name
from sgraph_ai_service_playwright__cli.vnc.service.Vnc__AWS__Client                 import TAG_PURPOSE_KEY, TAG_PURPOSE_VALUE, VNC_NAMING


VIEWER_PORT_EXTERNAL = 443                                                          # nginx TLS — chromium-VNC UI + proxied mitmweb


class Vnc__SG__Helper(Type_Safe):

    def ec2_client(self, region: str):                                              # Single seam — tests override
        from sgraph_ai_service_playwright__cli.credentials.service.Sg__Aws__Session  import Sg__Aws__Session
        from sgraph_ai_service_playwright__cli.credentials.service.Credentials__Store import Credentials__Store
        return Sg__Aws__Session(store=Credentials__Store()).boto3_client_from_context(
            service_name='ec2', region=region or '')

    def ensure_security_group(self, region: str, stack_name: Safe_Str__Vnc__Stack__Name,
                                     caller_ip: Safe_Str__IP__Address, public: bool = False) -> str:
        ec2     = self.ec2_client(region)
        sg_name = VNC_NAMING.sg_name_for_stack(stack_name)                          # "{stack}-sg" — never starts with reserved 'sg-'
        if public:                                                                  # `sp vnc create --open` — viewer is bcrypt-protected via nginx Basic auth so wider ingress is acceptable
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
                GroupName        = sg_name                                       ,
                Description      = f'SG VNC ephemeral stack: {str(stack_name)}'  ,  # ASCII only
                TagSpecifications= [{'ResourceType': 'security-group',
                                     'Tags': [{'Key': TAG_PURPOSE_KEY, 'Value': TAG_PURPOSE_VALUE}]}])
            sg_id = created.get('GroupId', '')

        try:                                                                        # Idempotent: AWS raises InvalidPermission.Duplicate if rule already exists
            ec2.authorize_security_group_ingress(
                GroupId      = sg_id,
                IpPermissions=[{'IpProtocol': 'tcp'                                                                          ,
                                'FromPort'  : VIEWER_PORT_EXTERNAL                                                            ,
                                'ToPort'    : VIEWER_PORT_EXTERNAL                                                            ,
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
