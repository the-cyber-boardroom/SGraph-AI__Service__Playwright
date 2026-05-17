# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Firefox: Firefox__Instance__Helper
# list_stacks, find_by_stack_name, terminate_instance.
# ═══════════════════════════════════════════════════════════════════════════════

from typing import Optional
from typing                                                                         import Dict, Optional

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute_specs.firefox.service.Firefox__Tags                          import (TAG_PURPOSE_KEY   ,
                                                                                             TAG_PURPOSE_VALUE ,
                                                                                             TAG_STACK_NAME_KEY)


class Firefox__Instance__Helper(Type_Safe):

    def ec2_client(self, region: str):                                              # Single seam — tests override
        from sgraph_ai_service_playwright__cli.credentials.service.Sg__Aws__Session  import Sg__Aws__Session
        from sgraph_ai_service_playwright__cli.credentials.service.Credentials__Store import Credentials__Store
        return Sg__Aws__Session(store=Credentials__Store()).boto3_client_from_context(
            service_name='ec2', region=region or '')

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
