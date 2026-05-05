# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Firefox: Firefox__SSM__Helper
# Sends shell commands to a running Firefox EC2 node via SSM send_command.
# Returns (success: bool, output: str).
# ═══════════════════════════════════════════════════════════════════════════════

import time

import boto3

from osbot_utils.type_safe.Type_Safe import Type_Safe


POLL_INTERVAL   = 1
POLL_MAX_SECS   = 30


class Firefox__SSM__Helper(Type_Safe):

    def ssm_client(self, region: str):
        return boto3.client('ssm', region_name=region)

    def run_command(self, region: str, instance_id: str, command: str) -> tuple:
        ssm = self.ssm_client(region)
        try:
            resp        = ssm.send_command(InstanceIds=[instance_id],
                                           DocumentName='AWS-RunShellScript',
                                           Parameters={'commands': [command]})
            command_id  = resp['Command']['CommandId']
        except Exception as e:
            return False, str(e)

        deadline = time.monotonic() + POLL_MAX_SECS
        while time.monotonic() < deadline:
            time.sleep(POLL_INTERVAL)
            try:
                inv    = ssm.get_command_invocation(CommandId=command_id, InstanceId=instance_id)
                status = inv.get('Status', '')
                if status == 'Success':
                    return True, inv.get('StandardOutputContent', '')
                if status in ('Failed', 'Cancelled', 'TimedOut', 'Undeliverable'):
                    return False, inv.get('StandardErrorContent', '') or status
            except ssm.exceptions.InvocationDoesNotExist:
                pass                                                               # command not yet picked up
        return False, f'timed out after {POLL_MAX_SECS}s'
