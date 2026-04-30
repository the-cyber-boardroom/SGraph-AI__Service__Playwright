# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Firefox__SSM__Helper
# Sends shell commands to a running Firefox EC2 instance via AWS SSM
# send_command (AWS-RunShellScript document). Requires the instance to have
# the AmazonSSMManagedInstanceCore IAM policy (same profile used at launch).
#
# Uses base64 encoding when writing file content so that any Python source
# (including special characters, quotes, heredoc markers) is transmitted
# safely without escaping concerns.
# ═══════════════════════════════════════════════════════════════════════════════

import base64
import time

import boto3                                                                        # EXCEPTION — narrow boto3 boundary

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.firefox.service.Firefox__User_Data__Builder  import INTERCEPTOR_FILE

POLL_INTERVAL_SEC = 1
TIMEOUT_SEC       = 30


class Firefox__SSM__Helper(Type_Safe):

    def ssm_client(self, region: str):
        return boto3.client('ssm', region_name=region)

    def write_file(self, region: str, instance_id: str, content: str, remote_path: str) -> tuple:  # → (success: bool, message: str)
        b64     = base64.b64encode(content.encode()).decode()
        command = f"echo '{b64}' | base64 -d > {remote_path}"
        return self._run(region, instance_id, [command])

    def _run(self, region: str, instance_id: str, commands: list) -> tuple:        # → (success: bool, message: str)
        ssm = self.ssm_client(region)
        try:
            resp       = ssm.send_command(InstanceIds     = [instance_id]          ,
                                          DocumentName    = 'AWS-RunShellScript'   ,
                                          Parameters      = {'commands': commands}  ,
                                          TimeoutSeconds  = TIMEOUT_SEC            )
            command_id = resp['Command']['CommandId']
        except Exception as exc:
            return False, f'send_command failed: {exc}'

        deadline = time.monotonic() + TIMEOUT_SEC
        while time.monotonic() < deadline:
            time.sleep(POLL_INTERVAL_SEC)
            try:
                inv    = ssm.get_command_invocation(CommandId=command_id, InstanceId=instance_id)
                status = inv.get('Status', '')
                if status in ('Pending', 'InProgress', 'Delayed'):
                    continue
                if status == 'Success':
                    return True, 'script updated'
                stderr = inv.get('StandardErrorContent', '').strip()
                return False, f'command failed ({status}): {stderr or "no stderr"}'
            except Exception as exc:
                return False, f'get_command_invocation failed: {exc}'

        return False, f'timed out waiting for SSM command after {TIMEOUT_SEC}s'

    def push_interceptor(self, region: str, instance_id: str, source: str) -> tuple:  # → (success: bool, message: str)
        return self.write_file(region, instance_id, source, INTERCEPTOR_FILE)
