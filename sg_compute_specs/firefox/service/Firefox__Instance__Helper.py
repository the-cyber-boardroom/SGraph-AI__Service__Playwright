# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Firefox: Firefox__Instance__Helper
# list_stacks, find_by_stack_name, terminate_instance.
# ═══════════════════════════════════════════════════════════════════════════════

from typing import Optional
from typing                                                                         import Dict, Optional

import boto3

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute_specs.firefox.service.Firefox__AWS__Client                          import (TAG_PURPOSE_KEY   ,
                                                                                             TAG_PURPOSE_VALUE ,
                                                                                             TAG_STACK_NAME_KEY)


class Firefox__Instance__Helper(Type_Safe):

    def ec2_client(self, region: str):
        return boto3.client('ec2', region_name=region)

    def list_stacks(self, region: str) -> Dict[str, dict]:
        ec2   = self.ec2_client(region)
        pages = ec2.get_paginator('describe_instances').paginate(
            Filters=[{'Name': f'tag:{TAG_PURPOSE_KEY}', 'Values': [TAG_PURPOSE_VALUE]              },
                     {'Name': 'instance-state-name'   , 'Values': ['pending', 'running', 'stopping', 'stopped']}])
        out: Dict[str, dict] = {}
        for page in pages:
            for reservation in page.get('Reservations', []):
                for details in reservation.get('Instances', []):
                    out[str(details.get('InstanceId', ''))] = details
        return out

    def find_by_stack_name(self, region: str, stack_name: str) -> Optional[dict]:
        for details in self.list_stacks(region).values():
            for tag in details.get('Tags', []):
                if tag.get('Key') == TAG_STACK_NAME_KEY and tag.get('Value') == stack_name:
                    return details
        return None

    def terminate_instance(self, region: str, instance_id: str) -> bool:
        try:
            self.ec2_client(region).terminate_instances(InstanceIds=[instance_id])
            return True
        except Exception:
            return False
