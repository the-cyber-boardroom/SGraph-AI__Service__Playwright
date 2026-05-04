# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Prometheus__SG__Helper
# Per-stack security group helper for sp prom. Mirrors OpenSearch__SG__Helper
# but opens port 9090 (Prometheus' own UI + API) instead of 443 — there is no
# nginx fronting in sp prom (P1: no UI in this stack; Grafana lives elsewhere).
#
# Single responsibility: SG existence + ingress on the Prometheus public port.
# ═══════════════════════════════════════════════════════════════════════════════

import boto3                                                                        # EXCEPTION — narrow boto3 boundary, see plan doc 2

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.prometheus.primitives.Safe_Str__IP__Address  import Safe_Str__IP__Address
from sgraph_ai_service_playwright__cli.prometheus.primitives.Safe_Str__Prom__Stack__Name import Safe_Str__Prom__Stack__Name
from sgraph_ai_service_playwright__cli.prometheus.service.Prometheus__AWS__Client   import PROM_NAMING, TAG_PURPOSE_KEY, TAG_PURPOSE_VALUE


PROMETHEUS_PORT_EXTERNAL = 9090                                                     # Prometheus' built-in UI + /api/v1/* + /-/healthy + /metrics


class Prometheus__SG__Helper(Type_Safe):

    def ec2_client(self, region: str):                                              # Single seam — tests override
        return boto3.client('ec2', region_name=region)

    def ensure_security_group(self, region: str, stack_name: Safe_Str__Prom__Stack__Name, caller_ip: Safe_Str__IP__Address) -> str:
        ec2     = self.ec2_client(region)
        sg_name = PROM_NAMING.sg_name_for_stack(stack_name)                         # "{stack}-sg" — never starts with reserved 'sg-'
        cidr    = f'{str(caller_ip)}/32'

        existing = ec2.describe_security_groups(
            Filters=[{'Name': 'group-name', 'Values': [sg_name]}]).get('SecurityGroups', [])

        if existing:
            sg_id = existing[0].get('GroupId', '')
        else:
            created = ec2.create_security_group(
                GroupName        = sg_name                                       ,
                Description      = f'SG Prometheus ephemeral stack: {str(stack_name)}',  # ASCII only — AWS rejects multi-byte GroupDescription
                TagSpecifications= [{'ResourceType': 'security-group',
                                     'Tags': [{'Key': TAG_PURPOSE_KEY, 'Value': TAG_PURPOSE_VALUE}]}])
            sg_id = created.get('GroupId', '')

        try:                                                                        # Idempotent: AWS raises InvalidPermission.Duplicate if rule already exists
            ec2.authorize_security_group_ingress(
                GroupId      = sg_id,
                IpPermissions=[{'IpProtocol': 'tcp'                                                                          ,
                                'FromPort'  : PROMETHEUS_PORT_EXTERNAL                                                       ,
                                'ToPort'    : PROMETHEUS_PORT_EXTERNAL                                                       ,
                                'IpRanges'  : [{'CidrIp': cidr, 'Description': 'sp-prom caller /32'}]}])
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
