# ═══════════════════════════════════════════════════════════════════════════════
# Ephemeral EC2 — EC2__Instance__Helper
# DescribeInstances, terminate, SSM reachability, and command execution.
# list_all_managed() / find_by_sg_stack_name() use the spec-service tag
# convention (sg:stack-name, sg:purpose) and find nodes from any spec.
# ═══════════════════════════════════════════════════════════════════════════════

import time
from typing                          import Dict, Optional

import boto3                                                                        # EXCEPTION — narrow boto3 boundary

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute.platforms.ec2.helpers.EC2__Tags__Builder import (TAG_PURPOSE_KEY  ,
                                                            TAG_PURPOSE_VALUE,
                                                            TAG_STACK_NAME  ,
                                                            TAG_STACK_TYPE  )

INSTANCE_STATES_LIVE = ['pending', 'running', 'stopping', 'stopped']


class EC2__Instance__Helper(Type_Safe):

    def ec2_client(self, region: str):
        return boto3.client('ec2', region_name=region)

    def ssm_client(self, region: str):
        return boto3.client('ssm', region_name=region)

    def list_by_stack_type(self, region: str, stack_type: str) -> Dict[str, dict]:
        resp = self.ec2_client(region).describe_instances(
            Filters=[{'Name': f'tag:{TAG_PURPOSE_KEY}' , 'Values': [TAG_PURPOSE_VALUE]},
                     {'Name': f'tag:{TAG_STACK_TYPE}'  , 'Values': [stack_type]       },
                     {'Name': 'instance-state-name'    , 'Values': INSTANCE_STATES_LIVE}])
        out = {}
        for reservation in resp.get('Reservations', []):
            for instance in reservation.get('Instances', []):
                iid = instance.get('InstanceId', '')
                if iid:
                    out[iid] = instance
        return out

    def find_by_stack_name(self, region: str, stack_name: str) -> Optional[dict]:
        resp = self.ec2_client(region).describe_instances(
            Filters=[{'Name': f'tag:{TAG_PURPOSE_KEY}', 'Values': [TAG_PURPOSE_VALUE]  },
                     {'Name': f'tag:{TAG_STACK_NAME}' , 'Values': [stack_name]         },
                     {'Name': 'instance-state-name'   , 'Values': INSTANCE_STATES_LIVE }])
        for reservation in resp.get('Reservations', []):
            for instance in reservation.get('Instances', []):
                return instance
        return None

    def list_all_managed(self, region: str) -> Dict[str, dict]:            # all spec-service nodes (tagged sg:stack-name)
        resp = self.ec2_client(region).describe_instances(
            Filters=[{'Name': 'tag-key'             , 'Values': ['sg:stack-name']  },
                     {'Name': 'instance-state-name' , 'Values': INSTANCE_STATES_LIVE}])
        out = {}
        for reservation in resp.get('Reservations', []):
            for instance in reservation.get('Instances', []):
                iid = instance.get('InstanceId', '')
                if iid:
                    out[iid] = instance
        return out

    def find_by_sg_stack_name(self, region: str, stack_name: str) -> Optional[dict]:
        resp = self.ec2_client(region).describe_instances(
            Filters=[{'Name': 'tag:sg:stack-name'   , 'Values': [stack_name]       },
                     {'Name': 'instance-state-name' , 'Values': INSTANCE_STATES_LIVE}])
        for reservation in resp.get('Reservations', []):
            for instance in reservation.get('Instances', []):
                return instance
        return None

    def terminate(self, region: str, instance_id: str) -> bool:
        try:
            self.ec2_client(region).terminate_instances(InstanceIds=[instance_id])
            return True
        except Exception:
            return False

    def wait_for_running(self, region: str, instance_id: str,
                         timeout_sec: int = 300, poll_sec: int = 10) -> bool:
        deadline = time.monotonic() + timeout_sec
        while time.monotonic() < deadline:
            resp = self.ec2_client(region).describe_instances(InstanceIds=[instance_id])
            for r in resp.get('Reservations', []):
                for inst in r.get('Instances', []):
                    if inst.get('State', {}).get('Name') == 'running':
                        return True
            time.sleep(poll_sec)
        return False

    def is_ssm_reachable(self, region: str, instance_id: str) -> bool:
        resp = self.ssm_client(region).describe_instance_information(
            Filters=[{'Key': 'InstanceIds', 'Values': [instance_id]}])
        return bool(resp.get('InstanceInformationList'))

    def run_command(self, region: str, instance_id: str, command: str,
                    timeout_sec: int = 60) -> tuple:
        # SSM SendCommand is fundamentally asynchronous — there is no
        # synchronous "run and return" endpoint. We poll get_command_invocation
        # tightly (200 ms) without an artificial pre-poll wait, and treat
        # InvocationDoesNotExist (the brief post-send propagation window) as
        # transient rather than fatal.
        # Returns (stdout: str, exit_code: int). exit_code -1 on timeout/error.
        # send_command failures (bad params, no permission, instance missing,
        # TimeoutSeconds < 30, etc.) are surfaced to stderr — silent empty returns
        # masked Bug B and Bug C for an entire session; do not regress.
        import sys
        _PENDING = {'Pending', 'InProgress', 'Delayed'}
        try:
            resp = self.ssm_client(region).send_command(
                InstanceIds    = [instance_id]          ,
                DocumentName   = 'AWS-RunShellScript'   ,
                Parameters     = {'commands': [command]},
                TimeoutSeconds = timeout_sec             )
        except Exception as exc:
            print(f'  [run_command] send_command failed: {type(exc).__name__}: {exc}',
                  file=sys.stderr)
            return '', -1
        command_id = resp.get('Command', {}).get('CommandId', '')
        if not command_id:
            print('  [run_command] send_command returned no CommandId',
                  file=sys.stderr)
            return '', -1
        deadline = time.monotonic() + timeout_sec
        inv      = {}
        while time.monotonic() < deadline:
            try:
                inv = self.ssm_client(region).get_command_invocation(
                    CommandId  = command_id ,
                    InstanceId = instance_id)
                if inv.get('StatusDetails', '') not in _PENDING:
                    rc = inv.get('ResponseCode')
                    return (inv.get('StandardOutputContent', '').strip(),
                            int(rc) if rc is not None else -1)
            except Exception:
                pass                         # InvocationDoesNotExist / transient — keep polling
            time.sleep(0.2)
        return inv.get('StandardOutputContent', '').strip(), -1
