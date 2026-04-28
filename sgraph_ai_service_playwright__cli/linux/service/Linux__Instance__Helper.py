# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Linux__Instance__Helper
# Instance lookup, termination, and SSM command execution for sp linux.
# Read-only discovery + terminate (launch lives in Linux__Launch__Helper).
# Also owns SSM exec — the only remote-code surface for linux stacks.
# ═══════════════════════════════════════════════════════════════════════════════

import boto3                                                                        # EXCEPTION — narrow boto3 boundary, see plan doc

from typing                                                                         import Dict, Optional

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.linux.primitives.Safe_Str__Linux__Stack__Name import Safe_Str__Linux__Stack__Name
from sgraph_ai_service_playwright__cli.linux.service.Linux__AWS__Client             import TAG_PURPOSE_KEY, TAG_PURPOSE_VALUE, TAG_STACK_NAME_KEY


INSTANCE_STATES_LIVE = ['pending', 'running', 'stopping', 'stopped']


class Linux__Instance__Helper(Type_Safe):

    def ec2_client(self, region: str):
        return boto3.client('ec2', region_name=region)

    def ssm_client(self, region: str):
        return boto3.client('ssm', region_name=region)

    def list_stacks(self, region: str) -> Dict[str, dict]:                          # instance_id → describe_instances() detail dict
        resp = self.ec2_client(region).describe_instances(
            Filters=[{'Name': f'tag:{TAG_PURPOSE_KEY}', 'Values': [TAG_PURPOSE_VALUE] },
                     {'Name': 'instance-state-name'   , 'Values': INSTANCE_STATES_LIVE}])
        out = {}
        for reservation in resp.get('Reservations', []):
            for instance in reservation.get('Instances', []):
                iid = instance.get('InstanceId', '')
                if iid:
                    out[iid] = instance
        return out

    def find_by_stack_name(self, region: str, stack_name: Safe_Str__Linux__Stack__Name) -> Optional[dict]:
        for details in self.list_stacks(region).values():
            for tag in details.get('Tags', []):
                if tag.get('Key') == TAG_STACK_NAME_KEY and tag.get('Value') == str(stack_name):
                    return details
        return None

    def terminate_instance(self, region: str, instance_id: str) -> bool:
        try:
            self.ec2_client(region).terminate_instances(InstanceIds=[instance_id])
            return True
        except Exception:
            return False

    def is_ssm_reachable(self, region: str, instance_id: str) -> bool:             # SSM lists the instance only after the agent is connected
        resp = self.ssm_client(region).describe_instance_information(
            Filters=[{'Key': 'InstanceIds', 'Values': [instance_id]}])
        return bool(resp.get('InstanceInformationList'))

    def run_command(self, region: str, instance_id: str, command: str) -> dict:    # Returns SendCommand response; caller polls CommandInvocations for output
        return self.ssm_client(region).send_command(
            InstanceIds    = [instance_id]                           ,
            DocumentName   = 'AWS-RunShellScript'                    ,
            Parameters     = {'commands': [command]}                 ,
            TimeoutSeconds = 60                                      )
