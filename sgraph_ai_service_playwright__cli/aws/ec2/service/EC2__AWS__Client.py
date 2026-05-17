# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/ec2 — EC2__AWS__Client
# Thin boto3 boundary for EC2 instance CRUD and queries.
# Wraps osbot_aws EC2 helpers where available; falls back to a direct boto3
# client() seam for operations not yet in osbot_aws.
#
# Mutation guard: callers check SG_AWS__EC2__ALLOW_MUTATIONS=1 before calling
# any create / start / stop / terminate method.
#
# Coexistence note (v0.2.29): the legacy Ec2__AWS__Client at
#   sgraph_ai_service_playwright__cli/ec2/service/Ec2__AWS__Client.py
# still owns ecr_registry_host, aws_account_id, aws_region helpers plus
# IAM profile management. This new client owns the general-purpose
# instance lifecycle surface. A v0.2.30 hygiene pass will consolidate.
# ═══════════════════════════════════════════════════════════════════════════════

import json
from typing import Optional

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws.ec2.collections.List__Schema__EC2__Instance  import List__Schema__EC2__Instance
from sgraph_ai_service_playwright__cli.aws.ec2.enums.Enum__EC2__Instance__State         import Enum__EC2__Instance__State
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__AMI_Id         import Safe_Str__EC2__AMI_Id
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__Instance_Id    import Safe_Str__EC2__Instance_Id
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__Instance__Type import Safe_Str__EC2__Instance__Type
from sgraph_ai_service_playwright__cli.aws.ec2.schemas.Schema__EC2__Instance            import Schema__EC2__Instance
from sgraph_ai_service_playwright__cli.aws.ec2.schemas.Schema__EC2__Instance__Detail    import Schema__EC2__Instance__Detail
from sgraph_ai_service_playwright__cli.aws.ec2.schemas.Schema__EC2__Create__Request     import Schema__EC2__Create__Request


class EC2__AWS__Client(Type_Safe):

    def client(self):                                                           # Single seam — subclass overrides for in-memory tests
        from sgraph_ai_service_playwright__cli.credentials.service.Sg__Aws__Session import Sg__Aws__Session
        return Sg__Aws__Session.from_context().boto3_client_from_context('ec2')

    # ── read ──────────────────────────────────────────────────────────────────

    def list_instances(self, state: str = 'all', name_prefix: str = '',
                       tag_filters: Optional[list] = None) -> List__Schema__EC2__Instance:
        ec2      = self.client()
        filters  = []
        if state and state != 'all':
            filters.append({'Name': 'instance-state-name', 'Values': [state]})
        if name_prefix:
            filters.append({'Name': 'tag:Name', 'Values': [f'{name_prefix}*']})
        if tag_filters:
            filters.extend(tag_filters)
        result   = List__Schema__EC2__Instance()
        kwargs   = {'Filters': filters} if filters else {}
        paginator = ec2.get_paginator('describe_instances')
        for page in paginator.paginate(**kwargs):
            for reservation in page.get('Reservations', []):
                for raw in reservation.get('Instances', []):
                    result.append(self._parse_summary(raw))
        return result

    def describe_instance(self, instance_id: str) -> Optional[Schema__EC2__Instance__Detail]:
        try:
            ec2   = self.client()
            resp  = ec2.describe_instances(InstanceIds=[instance_id])
            rsvs  = resp.get('Reservations', [])
            if not rsvs:
                return None
            instances = rsvs[0].get('Instances', [])
            if not instances:
                return None
            return self._parse_detail(instances[0])
        except Exception:
            return None

    def get_instance_tags(self, instance_id: str) -> dict:                     # Returns {Key: Value} map
        try:
            ec2  = self.client()
            resp = ec2.describe_tags(Filters=[
                {'Name': 'resource-id', 'Values': [instance_id]},
                {'Name': 'resource-type', 'Values': ['instance']},
            ])
            return {t['Key']: t['Value'] for t in resp.get('Tags', [])}
        except Exception:
            return {}

    def list_instance_types(self, family: str = '') -> list:                   # Returns list of instance type name strings
        ec2      = self.client()
        filters  = []
        if family:
            filters.append({'Name': 'instance-type', 'Values': [f'{family}.*']})
        result   = []
        paginator = ec2.get_paginator('describe_instance_types')
        for page in paginator.paginate(**({'Filters': filters} if filters else {})):
            for it in page.get('InstanceTypes', []):
                result.append(it.get('InstanceType', ''))
        return sorted(result)

    # ── mutations ─────────────────────────────────────────────────────────────

    def create_instance(self, request: Schema__EC2__Create__Request,
                        extra_tags: Optional[list] = None) -> Optional[str]:   # Returns new instance_id or None
        ec2   = self.client()
        tags  = [{'Key': 'Name', 'Value': request.name}] if request.name else []
        if extra_tags:
            tags.extend(extra_tags)
        kwargs = dict(
            ImageId      = str(request.ami_id),
            InstanceType = str(request.instance_type),
            MinCount     = 1,
            MaxCount     = 1,
        )
        if request.key_pair:
            kwargs['KeyName'] = request.key_pair
        if request.subnet_id:
            kwargs['SubnetId'] = request.subnet_id
        if request.security_groups:
            kwargs['SecurityGroupIds'] = [s.strip() for s in request.security_groups.split(',') if s.strip()]
        if request.user_data:
            kwargs['UserData'] = request.user_data
        if tags:
            kwargs['TagSpecifications'] = [{'ResourceType': 'instance', 'Tags': tags}]
        try:
            resp        = ec2.run_instances(**kwargs)
            instances   = resp.get('Instances', [])
            if not instances:
                return None
            return instances[0].get('InstanceId')
        except Exception:
            return None

    def start_instance(self, instance_id: str) -> bool:
        try:
            self.client().start_instances(InstanceIds=[instance_id])
            return True
        except Exception:
            return False

    def stop_instance(self, instance_id: str) -> bool:
        try:
            self.client().stop_instances(InstanceIds=[instance_id])
            return True
        except Exception:
            return False

    def terminate_instance(self, instance_id: str) -> bool:
        try:
            self.client().terminate_instances(InstanceIds=[instance_id])
            return True
        except Exception:
            return False

    def add_tags(self, instance_id: str, tags: dict) -> bool:                  # tags is {Key: Value} map
        try:
            self.client().create_tags(
                Resources = [instance_id],
                Tags      = [{'Key': k, 'Value': v} for k, v in tags.items()],
            )
            return True
        except Exception:
            return False

    def remove_tags(self, instance_id: str, keys: list) -> bool:
        try:
            self.client().delete_tags(
                Resources = [instance_id],
                Tags      = [{'Key': k} for k in keys],
            )
            return True
        except Exception:
            return False

    # ── internal ──────────────────────────────────────────────────────────────

    def _parse_summary(self, raw: dict) -> Schema__EC2__Instance:
        tags      = {t['Key']: t['Value'] for t in raw.get('Tags', [])}
        iid       = raw.get('InstanceId', '')
        itype     = raw.get('InstanceType', '')
        ami       = raw.get('ImageId', '')
        state_str = raw.get('State', {}).get('Name', 'unknown')
        try:
            state = Enum__EC2__Instance__State(state_str)
        except ValueError:
            state = Enum__EC2__Instance__State.UNKNOWN
        launch_raw = raw.get('LaunchTime')
        launch_str = str(launch_raw) if launch_raw else ''
        return Schema__EC2__Instance(
            instance_id   = Safe_Str__EC2__Instance_Id(iid)    if iid   else Safe_Str__EC2__Instance_Id(''),
            instance_type = Safe_Str__EC2__Instance__Type(itype) if itype else Safe_Str__EC2__Instance__Type(''),
            ami_id        = Safe_Str__EC2__AMI_Id(ami)          if ami   else Safe_Str__EC2__AMI_Id(''),
            state         = state,
            name          = tags.get('Name', ''),
            public_ip     = raw.get('PublicIpAddress', '') or '',
            private_ip    = raw.get('PrivateIpAddress', '') or '',
            launch_time   = launch_str,
            key_name      = raw.get('KeyName', '') or '',
        )

    def _parse_detail(self, raw: dict) -> Schema__EC2__Instance__Detail:
        tags     = {t['Key']: t['Value'] for t in raw.get('Tags', [])}
        iid      = raw.get('InstanceId', '')
        itype    = raw.get('InstanceType', '')
        ami      = raw.get('ImageId', '')
        state_str = raw.get('State', {}).get('Name', 'unknown')
        try:
            state = Enum__EC2__Instance__State(state_str)
        except ValueError:
            state = Enum__EC2__Instance__State.UNKNOWN
        launch_raw = raw.get('LaunchTime')
        launch_str = str(launch_raw) if launch_raw else ''
        iam_profile = ''
        if raw.get('IamInstanceProfile'):
            iam_profile = raw['IamInstanceProfile'].get('Arn', '')
        return Schema__EC2__Instance__Detail(
            instance_id          = Safe_Str__EC2__Instance_Id(iid)     if iid   else Safe_Str__EC2__Instance_Id(''),
            instance_type        = Safe_Str__EC2__Instance__Type(itype) if itype else Safe_Str__EC2__Instance__Type(''),
            ami_id               = Safe_Str__EC2__AMI_Id(ami)           if ami   else Safe_Str__EC2__AMI_Id(''),
            state                = state,
            name                 = tags.get('Name', ''),
            public_ip            = raw.get('PublicIpAddress', '')  or '',
            public_dns           = raw.get('PublicDnsName', '')    or '',
            private_ip           = raw.get('PrivateIpAddress', '') or '',
            private_dns          = raw.get('PrivateDnsName', '')   or '',
            launch_time          = launch_str,
            key_name             = raw.get('KeyName', '')          or '',
            vpc_id               = raw.get('VpcId', '')            or '',
            subnet_id            = raw.get('SubnetId', '')         or '',
            architecture         = raw.get('Architecture', '')     or '',
            platform             = raw.get('Platform', 'Linux')    or 'Linux',
            iam_instance_profile = iam_profile,
            root_device_type     = raw.get('RootDeviceType', '')   or '',
            tags_raw             = json.dumps(tags),
            security_groups_raw  = json.dumps(raw.get('SecurityGroups', [])),
            block_devices_raw    = json.dumps(raw.get('BlockDeviceMappings', [])),
        )
