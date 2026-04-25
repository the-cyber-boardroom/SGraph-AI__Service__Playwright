# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Elastic__AWS__Client__In_Memory
# Real subclass of Elastic__AWS__Client that drives every public method off
# fixture dictionaries. No boto3, no AWS round trips, no mocks.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                         import Dict, Optional

from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Elastic__Stack__Name import Safe_Str__Elastic__Stack__Name
from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__IP__Address     import Safe_Str__IP__Address
from sgraph_ai_service_playwright__cli.elastic.service.Elastic__AWS__Client         import (
    Elastic__AWS__Client,
    TAG_PURPOSE_KEY,
    TAG_PURPOSE_VALUE,
    TAG_STACK_NAME_KEY,
    TAG_ALLOWED_IP_KEY,
    TAG_CREATOR_KEY,
    aws_name_for_stack                                                              ,
    instance_tag                                                                    ,
)


DEFAULT_FIXTURE_AMI = 'ami-0123456789abcdef0'                                       # 17-char hex matching Safe_Str__AMI__Id


class Elastic__AWS__Client__In_Memory(Elastic__AWS__Client):
    fixture_ami         : str                                                       # AMI id returned by resolve_latest_al2023_ami
    fixture_instances   : Dict[str, dict]                                           # instance_id → describe_instances details (incl. Tags, State)
    fixture_sg_id       : str                                                       # Returned by ensure_security_group; tests can override via subclass
    last_sg_caller_ip   : str = ''                                                  # Captured for assertions
    last_launch_user_data: str = ''
    last_launch_ami     : str = ''
    terminated_ids      : list                                                      # Order-preserving record of terminate_instance calls
    deleted_sg_ids      : list
    ssm_calls           : list                                                      # [(instance_id, commands), ...] — captured for assertions
    fixture_ssm_stdout  : str = ''                                                  # What the next ssm_send_command returns
    fixture_ssm_stderr  : str = ''
    fixture_ssm_exit_code: int = 0
    fixture_ssm_status  : str = 'Success'
    fixture_profile_name: str = 'sg-elastic-ec2'                                    # Returned by ensure_instance_profile()
    last_launch_profile : str = ''                                                  # Captured for assertions on launch_instance(IamInstanceProfile.Name)
    last_launch_max_hours: int = 0                                                  # Captured for assertions on the auto-terminate timer

    def resolve_latest_al2023_ami(self, region: str) -> str:
        return self.fixture_ami or DEFAULT_FIXTURE_AMI

    def ensure_instance_profile(self, region: str) -> str:
        return self.fixture_profile_name

    def ensure_security_group(self, region    : str                          ,
                                    stack_name: Safe_Str__Elastic__Stack__Name,
                                    caller_ip : Safe_Str__IP__Address         ,
                                    creator   : str                           = ''
                               ) -> str:
        self.last_sg_caller_ip = str(caller_ip)
        return self.fixture_sg_id or 'sg-0fixture00000000'

    def launch_instance(self, region                : str                          ,
                              stack_name            : Safe_Str__Elastic__Stack__Name,
                              ami_id                : str                           ,
                              instance_type         : str                           ,
                              security_group_id     : str                           ,
                              user_data             : str                           ,
                              caller_ip             : Safe_Str__IP__Address         ,
                              instance_profile_name : str                           ,
                              creator               : str                           = '',
                              max_hours             : int                           = 0
                         ) -> str:
        self.last_launch_user_data = user_data
        self.last_launch_ami       = ami_id
        self.last_launch_profile   = str(instance_profile_name)
        self.last_launch_max_hours = int(max_hours)
        suffix      = f'{len(self.fixture_instances):017x}'                         # Stable, unique 17-hex suffix per launch
        instance_id = f'i-{suffix}'
        details = {'InstanceId'  : instance_id                                       ,
                   'ImageId'     : ami_id                                            ,
                   'InstanceType': instance_type                                     ,
                   'State'       : {'Name': 'pending'}                               ,
                   'PublicIpAddress': ''                                             ,
                   'SecurityGroups': [{'GroupId': security_group_id}]                ,
                   'Tags'        : [{'Key': 'Name'              , 'Value': aws_name_for_stack(stack_name)},
                                    {'Key': TAG_PURPOSE_KEY     , 'Value': TAG_PURPOSE_VALUE          } ,
                                    {'Key': TAG_STACK_NAME_KEY  , 'Value': str(stack_name)            } ,
                                    {'Key': TAG_ALLOWED_IP_KEY  , 'Value': str(caller_ip)             } ,
                                    {'Key': TAG_CREATOR_KEY     , 'Value': creator or ''              }]}
        self.fixture_instances[instance_id] = details
        return instance_id

    def list_elastic_instances(self, region: str) -> Dict[str, dict]:
        return dict(self.fixture_instances)

    def find_by_stack_name(self, region    : str                          ,
                                 stack_name: Safe_Str__Elastic__Stack__Name
                            ) -> Optional[dict]:
        name = str(stack_name)
        for details in self.fixture_instances.values():
            if instance_tag(details, TAG_STACK_NAME_KEY) == name:
                return details
        return None

    def terminate_instance(self, region: str, instance_id: str) -> bool:
        if instance_id in self.fixture_instances:
            self.terminated_ids.append(instance_id)
            self.fixture_instances[instance_id]['State'] = {'Name': 'shutting-down'}
            return True
        return False

    def delete_security_group(self, region: str, security_group_id: str) -> bool:
        self.deleted_sg_ids.append(security_group_id)
        return True

    def ssm_send_command(self, region, instance_id, commands, timeout=60):          # type: ignore[override]
        self.ssm_calls.append((str(instance_id), list(commands)))
        if instance_id not in self.fixture_instances:                               # No such instance — mirror the real client's "Failed" path
            return '', f'Unknown instance {instance_id}', -1, 'Failed'
        return (str(self.fixture_ssm_stdout)        ,
                str(self.fixture_ssm_stderr)        ,
                int(self.fixture_ssm_exit_code)     ,
                str(self.fixture_ssm_status or 'Success'))
