# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Elastic__AWS__Client
# Sole AWS boundary for the elastic sub-package. Every boto3 call for the
# ephemeral Elastic+Kibana lifecycle lives here so Elastic__Service can stay
# pure Python + Type_Safe schemas and the test in-memory subclass has a small,
# well-defined surface to implement.
#
# FOLLOW-UP: the rest of the repo forbids direct boto3 use (CLAUDE.md rule 8)
# and routes AWS operations through osbot-aws. The osbot-aws EC2 wrapper
# covers the majority of what this module does (describe / run / terminate),
# but `authorize_security_group_ingress` in osbot-aws does not yet accept a
# CidrIp argument, and locking a per-stack SG to the caller's /32 is the
# whole point of this slice. Keeping the entire client on raw boto3 gives us
# one import boundary rather than two, matching the Observability__AWS__Client
# precedent. Migrate to osbot-aws once CIDR-aware helpers exist there.
#
# Tag convention on every instance + SG created by this client:
#   Name              : elastic-{stack_name}         ← visible in EC2 console
#   sg:purpose        : elastic                      ← filter for list_stacks
#   sg:stack-name     : {stack_name}                 ← logical name lookup
#   sg:allowed-ip     : {caller_ip}                  ← records what /32 was set
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                         import Dict, Optional

import boto3                                                                        # EXCEPTION — see module header

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.type_safe_core.decorators.type_safe                      import type_safe

from sgraph_ai_service_playwright__cli.ec2.enums.Enum__Instance__State              import Enum__Instance__State
from sgraph_ai_service_playwright__cli.elastic.enums.Enum__Elastic__State           import Enum__Elastic__State
from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Elastic__Stack__Name import Safe_Str__Elastic__Stack__Name
from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__IP__Address     import Safe_Str__IP__Address
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Elastic__Info        import Schema__Elastic__Info


TAG_PURPOSE_KEY     = 'sg:purpose'
TAG_PURPOSE_VALUE   = 'elastic'
TAG_STACK_NAME_KEY  = 'sg:stack-name'
TAG_ALLOWED_IP_KEY  = 'sg:allowed-ip'
TAG_CREATOR_KEY     = 'sg:creator'

AL2023_SSM_PARAMETER = '/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64'

KIBANA_PORT_EXTERNAL = 443                                                          # nginx TLS; serves Kibana at / and ES at /_elastic/*


def instance_tag(details: dict, key: str) -> str:                                   # Helper mirroring scripts.provision_ec2._instance_tag
    for tag in details.get('Tags', []):
        if tag.get('Key') == key:
            return tag.get('Value', '')
    return ''


def elastic_state_from_ec2(state_str: str) -> Enum__Elastic__State:
    mapping = {Enum__Instance__State.PENDING.value      : Enum__Elastic__State.PENDING    ,
               Enum__Instance__State.RUNNING.value      : Enum__Elastic__State.RUNNING    ,
               Enum__Instance__State.SHUTTING_DOWN.value: Enum__Elastic__State.TERMINATING,
               Enum__Instance__State.TERMINATED.value   : Enum__Elastic__State.TERMINATED ,
               Enum__Instance__State.STOPPING.value     : Enum__Elastic__State.TERMINATING,
               Enum__Instance__State.STOPPED.value      : Enum__Elastic__State.TERMINATED }
    return mapping.get(state_str, Enum__Elastic__State.UNKNOWN)


class Elastic__AWS__Client(Type_Safe):                                              # Isolated boto3 boundary

    def ec2_client(self, region: str):                                              # Single seam — tests override to return a fake client
        return boto3.client('ec2', region_name=region)

    def ssm_client(self, region: str):
        return boto3.client('ssm', region_name=region)

    @type_safe
    def resolve_latest_al2023_ami(self, region: str) -> str:
        ssm   = self.ssm_client(region)
        param = ssm.get_parameter(Name=AL2023_SSM_PARAMETER)
        return str(param.get('Parameter', {}).get('Value', ''))

    @type_safe
    def ensure_security_group(self, region    : str                          ,
                                    stack_name: Safe_Str__Elastic__Stack__Name,
                                    caller_ip : Safe_Str__IP__Address         ,
                                    creator   : str                           = ''
                               ) -> str:
        ec2       = self.ec2_client(region)
        sg_name   = f'sg-elastic-{str(stack_name)}'
        cidr      = f'{str(caller_ip)}/32'

        existing = ec2.describe_security_groups(
            Filters=[{'Name': 'group-name', 'Values': [sg_name]}]                   # Default VPC in the region
        ).get('SecurityGroups', [])

        if existing:
            sg_id = existing[0].get('GroupId', '')
        else:
            created = ec2.create_security_group(
                GroupName  = sg_name                                          ,
                Description= f'SG Elastic ephemeral stack: {str(stack_name)}' ,
                TagSpecifications=[{
                    'ResourceType': 'security-group',
                    'Tags': self.build_tags(stack_name, caller_ip, creator)}]
            )
            sg_id = created.get('GroupId', '')

        try:                                                                        # Idempotent: AWS raises InvalidPermission.Duplicate if rule already exists
            ec2.authorize_security_group_ingress(
                GroupId = sg_id,
                IpPermissions=[{
                    'IpProtocol': 'tcp'                                    ,
                    'FromPort'  : KIBANA_PORT_EXTERNAL                      ,
                    'ToPort'    : KIBANA_PORT_EXTERNAL                      ,
                    'IpRanges'  : [{'CidrIp': cidr, 'Description': 'sg-elastic caller /32'}]
                }])
        except Exception as exc:
            if 'InvalidPermission.Duplicate' not in str(exc):
                raise
        return sg_id

    @type_safe
    def launch_instance(self, region        : str                          ,
                              stack_name    : Safe_Str__Elastic__Stack__Name,
                              ami_id        : str                           ,
                              instance_type : str                           ,
                              security_group_id: str                        ,
                              user_data     : str                           ,
                              caller_ip     : Safe_Str__IP__Address         ,
                              creator       : str                           = ''
                         ) -> str:
        ec2    = self.ec2_client(region)
        result = ec2.run_instances(
            ImageId          = ami_id                                    ,
            InstanceType     = instance_type                             ,
            MinCount         = 1                                          ,
            MaxCount         = 1                                          ,
            SecurityGroupIds = [security_group_id]                        ,
            UserData         = user_data                                  ,
            TagSpecifications=[{
                'ResourceType': 'instance',
                'Tags'        : self.build_tags(stack_name, caller_ip, creator)}]
        )
        instances = result.get('Instances', [])
        if not instances:
            return ''
        return str(instances[0].get('InstanceId', ''))

    @type_safe
    def list_elastic_instances(self, region: str) -> Dict[str, dict]:               # id → describe_instances details (filtered by sg:purpose=elastic)
        ec2    = self.ec2_client(region)
        pages  = ec2.get_paginator('describe_instances').paginate(
            Filters=[{'Name': f'tag:{TAG_PURPOSE_KEY}', 'Values': [TAG_PURPOSE_VALUE]},
                     {'Name': 'instance-state-name'   ,
                      'Values': ['pending', 'running', 'stopping', 'stopped']}]     # Skip terminated — they still appear in describe for a while
        )
        out: Dict[str, dict] = {}
        for page in pages:
            for reservation in page.get('Reservations', []):
                for details in reservation.get('Instances', []):
                    out[str(details.get('InstanceId', ''))] = details
        return out

    @type_safe
    def find_by_stack_name(self, region    : str                          ,
                                 stack_name: Safe_Str__Elastic__Stack__Name
                            ) -> Optional[dict]:
        name = str(stack_name)
        for details in self.list_elastic_instances(region).values():
            if instance_tag(details, TAG_STACK_NAME_KEY) == name:
                return details
        return None

    @type_safe
    def terminate_instance(self, region: str, instance_id: str) -> bool:
        ec2 = self.ec2_client(region)
        try:
            ec2.terminate_instances(InstanceIds=[instance_id])
            return True
        except Exception:
            return False

    @type_safe
    def delete_security_group(self, region: str, security_group_id: str) -> bool:
        ec2 = self.ec2_client(region)
        try:
            ec2.delete_security_group(GroupId=security_group_id)
            return True
        except Exception:                                                           # Often fails while the instance is still terminating — best effort
            return False

    def build_instance_info(self, details: dict) -> Schema__Elastic__Info:          # Shared mapper used by list + info
        state_raw = details.get('State', {})
        state_str = state_raw.get('Name', '') if isinstance(state_raw, dict) else str(state_raw)
        public_ip = details.get('PublicIpAddress', '') or ''
        sg_list   = details.get('SecurityGroups', [])
        sg_id     = str(sg_list[0].get('GroupId', '')) if sg_list else ''
        return Schema__Elastic__Info(stack_name       = instance_tag(details, TAG_STACK_NAME_KEY) ,
                                     aws_name_tag     = instance_tag(details, 'Name')             ,
                                     instance_id      = str(details.get('InstanceId', ''))        ,
                                     region           = details.get('__region', '')               ,  # Service attaches before mapping
                                     ami_id           = str(details.get('ImageId', ''))           ,
                                     instance_type    = str(details.get('InstanceType', ''))      ,
                                     security_group_id= sg_id                                      ,
                                     allowed_ip       = instance_tag(details, TAG_ALLOWED_IP_KEY) ,
                                     public_ip        = public_ip                                  ,
                                     kibana_url       = f'https://{public_ip}/' if public_ip else '',
                                     state            = elastic_state_from_ec2(state_str)         )

    def build_tags(self, stack_name: Safe_Str__Elastic__Stack__Name ,
                         caller_ip : Safe_Str__IP__Address         ,
                         creator   : str
                    ) -> list:
        return [{'Key': 'Name'            , 'Value': f'elastic-{str(stack_name)}'},  # Always prefixed — shown in EC2 console
                {'Key': TAG_PURPOSE_KEY   , 'Value': TAG_PURPOSE_VALUE          } ,
                {'Key': TAG_STACK_NAME_KEY, 'Value': str(stack_name)            } ,
                {'Key': TAG_ALLOWED_IP_KEY, 'Value': str(caller_ip)             } ,
                {'Key': TAG_CREATOR_KEY   , 'Value': creator or ''              }]
