# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Playwright__SG__Helper
# Per-stack security group helper for sp playwright. Mirrors Vnc__SG__Helper.
# Ingress on port 8000 (Playwright FastAPI — the operator-facing API).
# :19009 (host-control) is never published — reached via SSM port-forward.
# ═══════════════════════════════════════════════════════════════════════════════

import boto3                                                                     # EXCEPTION — narrow boto3 boundary, see plan doc 2

from osbot_utils.type_safe.Type_Safe                                             import Type_Safe

from sgraph_ai_service_playwright__cli.playwright.primitives.Safe_Str__IP__Address    import Safe_Str__IP__Address
from sgraph_ai_service_playwright__cli.playwright.primitives.Safe_Str__Playwright__Stack__Name import Safe_Str__Playwright__Stack__Name
from sgraph_ai_service_playwright__cli.playwright.service.Playwright__AWS__Client     import TAG_PURPOSE_KEY, TAG_PURPOSE_VALUE, PLAYWRIGHT_NAMING


PLAYWRIGHT_API_PORT = 8000                                                       # Playwright FastAPI — the public-facing API


class Playwright__SG__Helper(Type_Safe):

    def ec2_client(self, region: str):                                           # Single seam — tests override
        return boto3.client('ec2', region_name=region)

    def ensure_security_group(self, region: str, stack_name: Safe_Str__Playwright__Stack__Name,
                                     caller_ip: Safe_Str__IP__Address, public: bool = False) -> str:
        ec2     = self.ec2_client(region)
        sg_name = PLAYWRIGHT_NAMING.sg_name_for_stack(stack_name)                # "{stack}-sg" — never starts with reserved 'sg-'
        if public:
            cidr      = '0.0.0.0/0'
            cidr_desc = 'sp-playwright public ingress'
        else:
            cidr      = f'{str(caller_ip)}/32'
            cidr_desc = 'sp-playwright caller /32'

        existing = ec2.describe_security_groups(
            Filters=[{'Name': 'group-name', 'Values': [sg_name]}]).get('SecurityGroups', [])

        if existing:
            sg_id = existing[0].get('GroupId', '')
        else:
            created = ec2.create_security_group(
                GroupName        = sg_name                                               ,
                Description      = f'SP Playwright ephemeral stack: {str(stack_name)}'  ,
                TagSpecifications= [{'ResourceType': 'security-group',
                                     'Tags': [{'Key': TAG_PURPOSE_KEY, 'Value': TAG_PURPOSE_VALUE}]}])
            sg_id = created.get('GroupId', '')

        try:                                                                     # Idempotent: AWS raises InvalidPermission.Duplicate if rule already exists
            ec2.authorize_security_group_ingress(
                GroupId      = sg_id,
                IpPermissions=[{'IpProtocol': 'tcp'                                                                              ,
                                'FromPort'  : PLAYWRIGHT_API_PORT                                                                 ,
                                'ToPort'    : PLAYWRIGHT_API_PORT                                                                 ,
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
