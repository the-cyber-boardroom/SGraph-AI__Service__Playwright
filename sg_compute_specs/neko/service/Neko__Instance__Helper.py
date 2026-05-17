# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Neko: Neko__Instance__Helper
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                         import Dict, Optional

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute_specs.neko.primitives.Safe_Str__Neko__Stack__Name                   import Safe_Str__Neko__Stack__Name
from sg_compute_specs.neko.service.Neko__AWS__Client                                import TAG_PURPOSE_KEY, TAG_PURPOSE_VALUE, TAG_STACK_NAME_KEY


INSTANCE_STATES_LIVE = ['pending', 'running', 'stopping', 'stopped']


class Neko__Instance__Helper(Type_Safe):

    def ec2_client(self, region: str):                                              # Single seam — tests override
        from sgraph_ai_service_playwright__cli.credentials.service.Sg__Aws__Session  import Sg__Aws__Session
        from sgraph_ai_service_playwright__cli.credentials.service.Credentials__Store import Credentials__Store
        return Sg__Aws__Session(store=Credentials__Store()).boto3_client_from_context(
            service_name='ec2', region=region or '')

    def list_stacks(self, region: str) -> Dict[str, dict]:
        resp = self.ec2_client(region).describe_instances(
            Filters=[{'Name': f'tag:{TAG_PURPOSE_KEY}', 'Values': [TAG_PURPOSE_VALUE]},
                     {'Name': 'instance-state-name'   , 'Values': INSTANCE_STATES_LIVE}])
        out = {}
        for reservation in resp.get('Reservations', []):
            for instance in reservation.get('Instances', []):
                iid = instance.get('InstanceId', '')
                if iid:
                    out[iid] = instance
        return out

    def find_by_stack_name(self, region: str, stack_name: Safe_Str__Neko__Stack__Name) -> Optional[dict]:
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
