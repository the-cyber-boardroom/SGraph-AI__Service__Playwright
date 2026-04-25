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
#   Name              : <aws_name>                   ← visible in EC2 console
#   sg:purpose        : elastic                      ← filter for list_stacks
#   sg:stack-name     : {stack_name}                 ← logical name lookup
#   sg:allowed-ip     : {caller_ip}                  ← records what /32 was set
#
# Naming helpers: aws_name_for_stack() / sg_name_for_stack()
#   - AWS reserves the literal "sg-*" prefix for security group IDs, so the SG
#     GroupName must NOT start with "sg-". We use a "-sg" suffix instead.
#     See CLAUDE.md "AWS Resource Naming" rule.
#   - The AWS Name tag always carries an "elastic-" marker, but the helper
#     skips it when the logical stack_name already starts with that prefix —
#     avoids cosmetic doubles like "elastic-elastic-quiet-fermi".
# ═══════════════════════════════════════════════════════════════════════════════

import json
import time
from datetime                                                                       import datetime, timezone
from typing                                                                         import Dict, Optional, Tuple

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

INSTANCE_PROFILE_NAME = 'sg-elastic-ec2'                                            # IAM role + instance profile share the same name (single-purpose: AmazonSSMManagedInstanceCore for connect/exec)
SSM_MANAGED_POLICY_ARN = 'arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore'

IAM_ROLE_DESCRIPTION = 'SG ephemeral elastic - SSM agent access'                    # ASCII only. AWS IAM Description regex rejects em-dash (U+2014) and other multi-byte unicode.


EC2_TRUST_POLICY = {                                                                # AssumeRolePolicyDocument for an EC2-only role
    'Version'  : '2012-10-17',
    'Statement': [{'Effect'   : 'Allow'                                  ,
                   'Principal': {'Service': 'ec2.amazonaws.com'}         ,
                   'Action'   : 'sts:AssumeRole'                         }]
}


def instance_tag(details: dict, key: str) -> str:                                   # Helper mirroring scripts.provision_ec2._instance_tag
    for tag in details.get('Tags', []):
        if tag.get('Key') == key:
            return tag.get('Value', '')
    return ''


def aws_name_for_stack(stack_name: str) -> str:                                     # AWS Name tag — always carries an "elastic" marker, never doubled
    s = str(stack_name)
    return s if s.startswith('elastic-') else f'elastic-{s}'


def sg_name_for_stack(stack_name: str) -> str:                                      # SG GroupName — never starts with "sg-" (AWS reserves that prefix for SG IDs)
    return f'{str(stack_name)}-sg'


def launch_time_and_uptime(launch_time):                                            # Returns (iso_str, uptime_seconds). Boto3 hands us a datetime; tests pass a string or None.
    if launch_time is None or launch_time == '':
        return '', 0
    if isinstance(launch_time, datetime):
        dt = launch_time if launch_time.tzinfo else launch_time.replace(tzinfo=timezone.utc)
        return dt.isoformat(), max(int((datetime.now(timezone.utc) - dt).total_seconds()), 0)
    return str(launch_time), 0                                                      # Unknown shape — preserve the string, can't compute uptime


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

    def iam_client(self, region: str):                                              # IAM is a global service; region is ignored but kept for parameter symmetry
        return boto3.client('iam', region_name=region)

    @type_safe
    def ensure_instance_profile(self, region: str) -> str:                          # Idempotent: ensure role + instance profile + SSM policy attachment exist; returns profile name
        iam       = self.iam_client(region)
        name      = INSTANCE_PROFILE_NAME
        not_found = iam.exceptions.NoSuchEntityException

        try:                                                                        # 1) IAM role
            iam.get_role(RoleName=name)
        except not_found:
            iam.create_role(RoleName                  = name                          ,
                            AssumeRolePolicyDocument = json.dumps(EC2_TRUST_POLICY)   ,
                            Description              = IAM_ROLE_DESCRIPTION)

        try:                                                                        # 2) AmazonSSMManagedInstanceCore attachment (AWS no-ops if already attached)
            iam.attach_role_policy(RoleName=name, PolicyArn=SSM_MANAGED_POLICY_ARN)
        except Exception:
            pass

        try:                                                                        # 3) Instance profile (create only if missing)
            iam.get_instance_profile(InstanceProfileName=name)
        except not_found:
            iam.create_instance_profile(InstanceProfileName=name)

        self.ensure_role_in_instance_profile(iam, name)                             # 4) Link role <-> profile (idempotent, retries on IAM eventual consistency)
        return name

    def ensure_role_in_instance_profile(self, iam, name: str) -> None:              # Attach `name` role to `name` profile if not already — NEVER swallows errors silently; retries NoSuchEntity for IAM propagation
        for attempt in range(4):
            try:
                profile = iam.get_instance_profile(InstanceProfileName=name)
                roles   = profile.get('InstanceProfile', {}).get('Roles', [])
                if any(r.get('RoleName') == name for r in roles):
                    return                                                          # Already linked — idempotent no-op
                iam.add_role_to_instance_profile(InstanceProfileName=name, RoleName=name)
                return
            except iam.exceptions.NoSuchEntityException:                            # Profile or role not visible to IAM yet (just created) — back off and retry
                if attempt == 3:
                    raise
                time.sleep(5)
            except iam.exceptions.LimitExceededException:                           # Profile already has a (different) role — can't attach a second; caller needs to intervene
                raise

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
        sg_name   = sg_name_for_stack(stack_name)                                   # "{stack}-sg" — see module header (AWS reserves "sg-*")
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
    def launch_instance(self, region                : str                          ,
                              stack_name            : Safe_Str__Elastic__Stack__Name,
                              ami_id                : str                           ,
                              instance_type         : str                           ,
                              security_group_id     : str                           ,
                              user_data             : str                           ,
                              caller_ip             : Safe_Str__IP__Address         ,
                              instance_profile_name : str                           ,  # e.g. INSTANCE_PROFILE_NAME — required for SSM connect/exec
                              creator               : str                           = '',
                              max_hours             : int                           = 0   # When > 0, instance terminates on shutdown (paired with the user-data systemd-run timer)
                         ) -> str:
        ec2    = self.ec2_client(region)
        kwargs = dict(
            ImageId          = ami_id                                    ,
            InstanceType     = instance_type                             ,
            MinCount         = 1                                          ,
            MaxCount         = 1                                          ,
            SecurityGroupIds = [security_group_id]                        ,
            UserData         = user_data                                  ,
            TagSpecifications=[{
                'ResourceType': 'instance',
                'Tags'        : self.build_tags(stack_name, caller_ip, creator)}],
            IamInstanceProfile = {'Name': str(instance_profile_name)}     ,  # SSM agent uses this role to register with Systems Manager
        )
        if max_hours > 0:                                                            # Pair with the shutdown timer in user-data so `shutdown -h now` actually terminates the instance instead of just stopping it
            kwargs['InstanceInitiatedShutdownBehavior'] = 'terminate'
        for attempt in range(3):                                                    # IAM is eventually consistent — retry on InvalidParameterValue mentioning the profile
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

    @type_safe
    def describe_security_group_ingress(self, region: str, security_group_id: str) -> list:  # Returns list of {'port': N, 'cidr': '1.2.3.4/32'} — drives the SG-vs-current-IP health check
        ec2 = self.ec2_client(region)
        try:
            response = ec2.describe_security_groups(GroupIds=[security_group_id])
        except Exception:
            return []
        groups = response.get('SecurityGroups', [])
        if not groups:
            return []
        rules = []
        for permission in groups[0].get('IpPermissions', []) or []:
            from_port = permission.get('FromPort')                                  # AWS reports from/to-port for a range; port 443 has both = 443
            for ip_range in permission.get('IpRanges', []) or []:
                rules.append({'port': from_port, 'cidr': str(ip_range.get('CidrIp', ''))})
        return rules

    @type_safe
    def ssm_send_command(self, region     : str  ,
                               instance_id: str  ,
                               commands   : list ,
                               timeout    : int  = 60
                          ) -> Tuple[str, str, int, str]:                           # (stdout, stderr, exit_code, status); exit_code = -1 on timeout/error
        ssm = self.ssm_client(region)
        try:
            response   = ssm.send_command(InstanceIds    = [instance_id]          ,
                                          DocumentName   = 'AWS-RunShellScript'   ,
                                          Parameters     = {'commands': commands} ,
                                          TimeoutSeconds = max(30, timeout)       )
        except Exception as exc:
            return '', f'SSM send_command failed: {exc}', -1, 'Failed'
        command_id = response['Command']['CommandId']
        deadline   = time.time() + timeout + 10
        while time.time() < deadline:
            time.sleep(2)
            try:
                inv = ssm.get_command_invocation(CommandId=command_id, InstanceId=instance_id)
            except ssm.exceptions.InvocationDoesNotExist:
                continue
            status = str(inv.get('Status', ''))
            if status not in ('Pending', 'InProgress', 'Delayed'):
                return (str(inv.get('StandardOutputContent', '')) ,
                        str(inv.get('StandardErrorContent', ''))  ,
                        int(inv.get('ResponseCode', -1) or -1)    ,
                        status                                    )
        return '', 'Timed out waiting for SSM command result', -1, 'TimedOut'

    def build_instance_info(self, details: dict) -> Schema__Elastic__Info:          # Shared mapper used by list + info
        state_raw = details.get('State', {})
        state_str = state_raw.get('Name', '') if isinstance(state_raw, dict) else str(state_raw)
        public_ip = details.get('PublicIpAddress', '') or ''
        sg_list   = details.get('SecurityGroups', [])
        sg_id     = str(sg_list[0].get('GroupId', '')) if sg_list else ''
        launch_raw, uptime_secs = launch_time_and_uptime(details.get('LaunchTime'))  # Compute once — list() and info() both render uptime so the mapper owns both
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
                                     state            = elastic_state_from_ec2(state_str)         ,
                                     launch_time      = launch_raw                                  ,
                                     uptime_seconds   = uptime_secs                                 )

    def build_tags(self, stack_name: Safe_Str__Elastic__Stack__Name ,
                         caller_ip : Safe_Str__IP__Address         ,
                         creator   : str
                    ) -> list:
        return [{'Key': 'Name'            , 'Value': aws_name_for_stack(stack_name)},  # Always carries "elastic-" marker; no doubles when stack_name already has it
                {'Key': TAG_PURPOSE_KEY   , 'Value': TAG_PURPOSE_VALUE            } ,
                {'Key': TAG_STACK_NAME_KEY, 'Value': str(stack_name)              } ,
                {'Key': TAG_ALLOWED_IP_KEY, 'Value': str(caller_ip)               } ,
                {'Key': TAG_CREATOR_KEY   , 'Value': creator or ''                }]
