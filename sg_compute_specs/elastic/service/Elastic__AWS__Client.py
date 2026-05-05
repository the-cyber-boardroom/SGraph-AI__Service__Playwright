# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Elastic: Elastic__AWS__Client
# ═══════════════════════════════════════════════════════════════════════════════

import json
import time
from datetime                                                                       import datetime, timezone
from typing                                                                         import Dict, Optional

import boto3

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute.platforms.ec2.helpers.Stack__Naming                            import Stack__Naming
from sg_compute.platforms.ec2.enums.Enum__Instance__State              import Enum__Instance__State
from sg_compute_specs.elastic.enums.Enum__Elastic__State                            import Enum__Elastic__State
from sg_compute_specs.elastic.primitives.Safe_Str__Elastic__Stack__Name             import Safe_Str__Elastic__Stack__Name
from sg_compute_specs.elastic.primitives.Safe_Str__IP__Address                      import Safe_Str__IP__Address
from sg_compute_specs.elastic.schemas.Schema__Elastic__Info                         import Schema__Elastic__Info


TAG_PURPOSE_KEY    = 'sg:purpose'
TAG_PURPOSE_VALUE  = 'elastic'
TAG_STACK_NAME_KEY = 'sg:stack-name'
TAG_ALLOWED_IP_KEY = 'sg:allowed-ip'
TAG_CREATOR_KEY    = 'sg:creator'

AL2023_SSM_PARAMETER  = '/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64'
KIBANA_PORT_EXTERNAL  = 443

INSTANCE_PROFILE_NAME = 'sg-elastic-ec2'
SSM_MANAGED_POLICY_ARN = 'arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore'
IAM_ROLE_DESCRIPTION   = 'SG ephemeral elastic - SSM agent access'

EC2_TRUST_POLICY = {'Version'  : '2012-10-17',
                    'Statement': [{'Effect'   : 'Allow'                        ,
                                   'Principal': {'Service': 'ec2.amazonaws.com'},
                                   'Action'   : 'sts:AssumeRole'               }]}

ELASTIC_NAMING = Stack__Naming(section_prefix='elastic')


def instance_tag(details: dict, key: str) -> str:
    for tag in details.get('Tags', []):
        if tag.get('Key') == key:
            return tag.get('Value', '')
    return ''


def launch_time_and_uptime(launch_time):
    if launch_time is None or launch_time == '':
        return '', 0
    if isinstance(launch_time, datetime):
        dt = launch_time if launch_time.tzinfo else launch_time.replace(tzinfo=timezone.utc)
        return dt.isoformat(), max(int((datetime.now(timezone.utc) - dt).total_seconds()), 0)
    return str(launch_time), 0


def elastic_state_from_ec2(state_str: str) -> Enum__Elastic__State:
    mapping = {Enum__Instance__State.PENDING.value      : Enum__Elastic__State.PENDING    ,
               Enum__Instance__State.RUNNING.value      : Enum__Elastic__State.RUNNING    ,
               Enum__Instance__State.SHUTTING_DOWN.value: Enum__Elastic__State.TERMINATING,
               Enum__Instance__State.TERMINATED.value   : Enum__Elastic__State.TERMINATED ,
               Enum__Instance__State.STOPPING.value     : Enum__Elastic__State.TERMINATING,
               Enum__Instance__State.STOPPED.value      : Enum__Elastic__State.TERMINATED }
    return mapping.get(state_str, Enum__Elastic__State.UNKNOWN)


class Elastic__AWS__Client(Type_Safe):

    def ec2_client(self, region: str):
        return boto3.client('ec2', region_name=region)

    def ssm_client(self, region: str):
        return boto3.client('ssm', region_name=region)

    def iam_client(self, region: str):
        return boto3.client('iam', region_name=region)

    def resolve_latest_al2023_ami(self, region: str) -> str:
        ssm   = self.ssm_client(region)
        param = ssm.get_parameter(Name=AL2023_SSM_PARAMETER)
        return str(param.get('Parameter', {}).get('Value', ''))

    def ensure_instance_profile(self, region: str) -> str:
        iam       = self.iam_client(region)
        name      = INSTANCE_PROFILE_NAME
        not_found = iam.exceptions.NoSuchEntityException
        try:
            iam.get_role(RoleName=name)
        except not_found:
            iam.create_role(RoleName                 = name                        ,
                            AssumeRolePolicyDocument = json.dumps(EC2_TRUST_POLICY),
                            Description              = IAM_ROLE_DESCRIPTION        )
        try:
            iam.attach_role_policy(RoleName=name, PolicyArn=SSM_MANAGED_POLICY_ARN)
        except Exception:
            pass
        try:
            iam.get_instance_profile(InstanceProfileName=name)
        except not_found:
            iam.create_instance_profile(InstanceProfileName=name)
        self._ensure_role_in_profile(iam, name)
        return name

    def _ensure_role_in_profile(self, iam, name: str) -> None:
        for attempt in range(4):
            try:
                profile = iam.get_instance_profile(InstanceProfileName=name)
                roles   = profile.get('InstanceProfile', {}).get('Roles', [])
                if any(r.get('RoleName') == name for r in roles):
                    return
                iam.add_role_to_instance_profile(InstanceProfileName=name, RoleName=name)
                return
            except iam.exceptions.NoSuchEntityException:
                if attempt == 3:
                    raise
                time.sleep(5)
            except iam.exceptions.LimitExceededException:
                raise

    def ensure_security_group(self, region: str, stack_name: Safe_Str__Elastic__Stack__Name,
                                     caller_ip: Safe_Str__IP__Address, creator: str = '') -> str:
        ec2     = self.ec2_client(region)
        sg_name = ELASTIC_NAMING.sg_name_for_stack(stack_name)
        cidr    = f'{str(caller_ip)}/32'

        existing = ec2.describe_security_groups(
            Filters=[{'Name': 'group-name', 'Values': [sg_name]}]).get('SecurityGroups', [])

        if existing:
            sg_id = existing[0].get('GroupId', '')
        else:
            created = ec2.create_security_group(
                GroupName        = sg_name                                              ,
                Description      = f'SG Elastic ephemeral stack: {str(stack_name)}'    ,
                TagSpecifications= [{'ResourceType': 'security-group',
                                     'Tags': self.build_tags(stack_name, caller_ip, creator)}])
            sg_id = created.get('GroupId', '')

        try:
            ec2.authorize_security_group_ingress(
                GroupId      = sg_id,
                IpPermissions=[{'IpProtocol': 'tcp'                                                              ,
                                'FromPort'  : KIBANA_PORT_EXTERNAL                                               ,
                                'ToPort'    : KIBANA_PORT_EXTERNAL                                               ,
                                'IpRanges'  : [{'CidrIp': cidr, 'Description': 'sg-elastic caller /32'}]}])
        except Exception as exc:
            if 'InvalidPermission.Duplicate' not in str(exc):
                raise
        return sg_id

    def launch_instance(self, region: str, stack_name: Safe_Str__Elastic__Stack__Name,
                              ami_id: str, instance_type: str, security_group_id: str,
                              user_data: str, caller_ip: Safe_Str__IP__Address,
                              instance_profile_name: str, creator: str = '', max_hours: int = 0) -> str:
        ec2    = self.ec2_client(region)
        kwargs = dict(ImageId          = ami_id                                          ,
                      InstanceType     = instance_type                                   ,
                      MinCount         = 1                                                ,
                      MaxCount         = 1                                                ,
                      SecurityGroupIds = [security_group_id]                             ,
                      UserData         = user_data                                        ,
                      TagSpecifications= [{'ResourceType': 'instance',
                                           'Tags': self.build_tags(stack_name, caller_ip, creator)}],
                      IamInstanceProfile = {'Name': str(instance_profile_name)}          )
        if max_hours > 0:
            kwargs['InstanceInitiatedShutdownBehavior'] = 'terminate'
        for attempt in range(3):
            try:
                result = ec2.run_instances(**kwargs)
                break
            except Exception as exc:
                msg = str(exc)
                if attempt < 2 and 'InvalidParameterValue' in msg and 'instance profile' in msg.lower():
                    time.sleep(5)
                    continue
                raise
        instances = result.get('Instances', [])
        return str(instances[0].get('InstanceId', '')) if instances else ''

    def list_elastic_instances(self, region: str) -> Dict[str, dict]:
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

    def find_by_stack_name(self, region: str, stack_name: Safe_Str__Elastic__Stack__Name) -> Optional[dict]:
        name = str(stack_name)
        for details in self.list_elastic_instances(region).values():
            if instance_tag(details, TAG_STACK_NAME_KEY) == name:
                return details
        return None

    def terminate_instance(self, region: str, instance_id: str) -> bool:
        try:
            self.ec2_client(region).terminate_instances(InstanceIds=[instance_id])
            return True
        except Exception:
            return False

    def delete_security_group(self, region: str, security_group_id: str) -> bool:
        try:
            self.ec2_client(region).delete_security_group(GroupId=security_group_id)
            return True
        except Exception:
            return False

    def build_instance_info(self, details: dict) -> Schema__Elastic__Info:
        state_raw  = details.get('State', {})
        state_str  = state_raw.get('Name', '') if isinstance(state_raw, dict) else str(state_raw)
        public_ip  = details.get('PublicIpAddress', '') or ''
        sg_list    = details.get('SecurityGroups', [])
        sg_id      = str(sg_list[0].get('GroupId', '')) if sg_list else ''
        launch_raw, uptime_secs = launch_time_and_uptime(details.get('LaunchTime'))
        return Schema__Elastic__Info(stack_name        = instance_tag(details, TAG_STACK_NAME_KEY),
                                     aws_name_tag      = instance_tag(details, 'Name')            ,
                                     instance_id       = str(details.get('InstanceId', ''))       ,
                                     region            = details.get('__region', '')              ,
                                     ami_id            = str(details.get('ImageId', ''))          ,
                                     instance_type     = str(details.get('InstanceType', ''))     ,
                                     security_group_id = sg_id                                    ,
                                     allowed_ip        = instance_tag(details, TAG_ALLOWED_IP_KEY),
                                     public_ip         = public_ip                                ,
                                     kibana_url        = f'https://{public_ip}/' if public_ip else '',
                                     state             = elastic_state_from_ec2(state_str)        ,
                                     launch_time       = launch_raw                               ,
                                     uptime_seconds    = uptime_secs                              )

    def build_tags(self, stack_name: Safe_Str__Elastic__Stack__Name,
                         caller_ip : Safe_Str__IP__Address         ,
                         creator   : str) -> list:
        return [{'Key': 'Name'            , 'Value': ELASTIC_NAMING.aws_name_for_stack(stack_name)},
                {'Key': TAG_PURPOSE_KEY   , 'Value': TAG_PURPOSE_VALUE                            },
                {'Key': TAG_STACK_NAME_KEY, 'Value': str(stack_name)                              },
                {'Key': TAG_ALLOWED_IP_KEY, 'Value': str(caller_ip)                               },
                {'Key': TAG_CREATOR_KEY   , 'Value': creator or ''                                }]
