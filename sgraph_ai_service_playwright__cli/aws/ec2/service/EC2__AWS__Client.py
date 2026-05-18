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

import re
from typing import Optional

from botocore.exceptions import ClientError
from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws.ec2.collections.Dict__EC2__Tag                         import Dict__EC2__Tag
from sgraph_ai_service_playwright__cli.aws.ec2.collections.List__Schema__EC2__AMI                  import List__Schema__EC2__AMI
from sgraph_ai_service_playwright__cli.aws.ec2.collections.List__Schema__EC2__Block_Device__Mapping import List__Schema__EC2__Block_Device__Mapping
from sgraph_ai_service_playwright__cli.aws.ec2.collections.List__Schema__EC2__Instance             import List__Schema__EC2__Instance
from sgraph_ai_service_playwright__cli.aws.ec2.collections.List__Schema__EC2__SG_Rule              import List__Schema__EC2__SG_Rule
from sgraph_ai_service_playwright__cli.aws.ec2.collections.List__Schema__EC2__Security_Group       import List__Schema__EC2__Security_Group
from sgraph_ai_service_playwright__cli.aws.ec2.collections.List__Schema__EC2__Security_Group__Ref  import List__Schema__EC2__Security_Group__Ref
from sgraph_ai_service_playwright__cli.aws.ec2.collections.List__Schema__EC2__Snapshot             import List__Schema__EC2__Snapshot
from sgraph_ai_service_playwright__cli.aws.ec2.enums.Enum__EC2__Instance__State                    import Enum__EC2__Instance__State
from sgraph_ai_service_playwright__cli.aws.ec2.enums.Enum__EC2__SG_Rule_Direction                  import Enum__EC2__SG_Rule_Direction
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__AMI_Id                    import Safe_Str__EC2__AMI_Id
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__ENI_Id                    import Safe_Str__EC2__ENI_Id
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__Instance_Id               import Safe_Str__EC2__Instance_Id
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__Instance__Type            import Safe_Str__EC2__Instance__Type
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__SG_Id                     import Safe_Str__EC2__SG_Id
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__Snapshot_Id               import Safe_Str__EC2__Snapshot_Id
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__VPC_Id                    import Safe_Str__EC2__VPC_Id
from sgraph_ai_service_playwright__cli.aws.ec2.schemas.Schema__EC2__AMI                            import Schema__EC2__AMI
from sgraph_ai_service_playwright__cli.aws.ec2.schemas.Schema__EC2__Block_Device__Mapping          import Schema__EC2__Block_Device__Mapping
from sgraph_ai_service_playwright__cli.aws.ec2.schemas.Schema__EC2__Create__Request                import Schema__EC2__Create__Request
from sgraph_ai_service_playwright__cli.aws.ec2.schemas.Schema__EC2__Instance                       import Schema__EC2__Instance
from sgraph_ai_service_playwright__cli.aws.ec2.schemas.Schema__EC2__Instance__Detail               import Schema__EC2__Instance__Detail
from sgraph_ai_service_playwright__cli.aws.ec2.schemas.Schema__EC2__SG_Rule                        import Schema__EC2__SG_Rule
from sgraph_ai_service_playwright__cli.aws.ec2.schemas.Schema__EC2__Security_Group                 import Schema__EC2__Security_Group
from sgraph_ai_service_playwright__cli.aws.ec2.schemas.Schema__EC2__Security_Group__Ref            import Schema__EC2__Security_Group__Ref
from sgraph_ai_service_playwright__cli.aws.ec2.schemas.Schema__EC2__Snapshot                       import Schema__EC2__Snapshot
from sgraph_ai_service_playwright__cli.credentials.service.Sg__Aws__Session                        import Sg__Aws__Session


_AMI_ID_RE = re.compile(r'^ami-[0-9a-f]{8,17}$')                                # Used by describe_ami to choose ImageIds vs name filter
_SG_ID_RE  = re.compile(r'^sg-[0-9a-f]{8,17}$')                                 # Used by describe_security_group to choose GroupIds vs group-name filter


class EC2__AWS__Client(Type_Safe):
    session : Sg__Aws__Session = None                                           # cached session — injected or lazy-init via setup()

    def setup(self):                                                             # idempotent — noop if session already set
        if self.session is None:
            self.session = Sg__Aws__Session.from_context()
        return self

    def client(self):                                                           # Single seam — subclass overrides for in-memory tests
        self.setup()
        return self.session.boto3_client_from_context('ec2')

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
        except ClientError as exc:
            code = exc.response.get('Error', {}).get('Code', '')
            if code == 'InvalidInstanceID.NotFound':
                return None
            raise

    def get_instance_tags(self, instance_id: str) -> dict:                     # Returns {Key: Value} map
        ec2  = self.client()
        resp = ec2.describe_tags(Filters=[
            {'Name': 'resource-id', 'Values': [instance_id]},
            {'Name': 'resource-type', 'Values': ['instance']},
        ])
        return {t['Key']: t['Value'] for t in resp.get('Tags', [])}

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

    # ── read: AMIs ────────────────────────────────────────────────────────────

    def list_amis(self, owner: str = 'self', name_substring: str = ''
                  ) -> List__Schema__EC2__AMI:
        ec2     = self.client()
        kwargs  = {}
        if owner and owner != 'all':                                            # 'all' → omit Owners (this can be huge — caller asked for it)
            kwargs['Owners'] = [owner]
        filters = []
        if name_substring:
            filters.append({'Name': 'name', 'Values': [f'*{name_substring}*']})
        if filters:
            kwargs['Filters'] = filters
        result    = List__Schema__EC2__AMI()
        paginator = ec2.get_paginator('describe_images')
        for page in paginator.paginate(**kwargs):
            for raw in page.get('Images', []):
                result.append(self._parse_ami(raw))
        return result

    def describe_ami(self, ami_id_or_name: str) -> Optional[Schema__EC2__AMI]:
        try:
            ec2 = self.client()
            if _AMI_ID_RE.match(ami_id_or_name):                                # Resolve by ImageIds
                resp   = ec2.describe_images(ImageIds=[ami_id_or_name])
                images = resp.get('Images', []) or []
            else:                                                                # Resolve by name; multiple → most-recent
                resp   = ec2.describe_images(Filters=[{'Name': 'name', 'Values': [ami_id_or_name]}])
                images = resp.get('Images', []) or []
                if len(images) > 1:
                    images = sorted(images, key=lambda i: i.get('CreationDate', ''),
                                    reverse=True)
            if not images:
                return None
            return self._parse_ami(images[0])
        except ClientError as exc:
            code = exc.response.get('Error', {}).get('Code', '')
            if code in ('InvalidAMIID.NotFound', 'InvalidAMIID.Malformed'):
                return None
            raise

    # ── read: snapshots ──────────────────────────────────────────────────────

    def list_snapshots(self, owner: str = 'self') -> List__Schema__EC2__Snapshot:
        ec2     = self.client()
        kwargs  = {}
        if owner and owner != 'all':
            kwargs['OwnerIds'] = [owner]
        result    = List__Schema__EC2__Snapshot()
        paginator = ec2.get_paginator('describe_snapshots')
        for page in paginator.paginate(**kwargs):
            for raw in page.get('Snapshots', []):
                result.append(self._parse_snapshot(raw))
        return result

    # ── read: security groups ────────────────────────────────────────────────

    def list_security_groups(self, vpc_id: str = '', name_substring: str = ''
                             ) -> List__Schema__EC2__Security_Group:
        ec2     = self.client()
        filters = []
        if vpc_id:
            filters.append({'Name': 'vpc-id', 'Values': [vpc_id]})
        if name_substring:                                                      # 'group-name' filter supports * wildcard server-side
            filters.append({'Name': 'group-name', 'Values': [f'*{name_substring}*']})
        kwargs    = {'Filters': filters} if filters else {}
        result    = List__Schema__EC2__Security_Group()
        paginator = ec2.get_paginator('describe_security_groups')
        for page in paginator.paginate(**kwargs):
            for raw in page.get('SecurityGroups', []) or []:
                result.append(self._parse_security_group(raw))                 # attached_eni_ids / attached_instance_ids left empty here (list view stays fast)
        return result

    def describe_security_group(self, sg_id_or_name: str, vpc_id: str = ''
                                ) -> Optional[Schema__EC2__Security_Group]:
        try:
            ec2 = self.client()
            if _SG_ID_RE.match(sg_id_or_name):                                  # Resolve by GroupIds
                resp   = ec2.describe_security_groups(GroupIds=[sg_id_or_name])
                groups = resp.get('SecurityGroups', []) or []
            else:                                                               # Resolve by name; narrow with VpcId when given
                filters = [{'Name': 'group-name', 'Values': [sg_id_or_name]}]
                if vpc_id:
                    filters.append({'Name': 'vpc-id', 'Values': [vpc_id]})
                resp   = ec2.describe_security_groups(Filters=filters)
                groups = resp.get('SecurityGroups', []) or []
                if len(groups) > 1:                                             # SG names are scoped per-VPC — ambiguity is a real bug, never silently pick
                    vpcs = ', '.join(sorted({g.get('VpcId', '') for g in groups}))
                    raise ValueError(
                        f'Ambiguous security-group name {sg_id_or_name!r}: matches in VPCs [{vpcs}]. '
                        f'Re-run with --vpc to disambiguate.')
            if not groups:
                return None
            sg = self._parse_security_group(groups[0])
            # ── populate attached_eni_ids / attached_instance_ids ────────────
            eni_records = self.list_network_interfaces(sg_id=str(sg.sg_id))
            eni_ids       = []
            instance_ids  = []
            seen_eni      = set()
            seen_instance = set()
            for eni in eni_records:
                eid = eni.get('NetworkInterfaceId', '') or ''
                if eid and eid not in seen_eni:
                    seen_eni.add(eid)
                    eni_ids.append(Safe_Str__EC2__ENI_Id(eid))
                iid = (eni.get('Attachment') or {}).get('InstanceId', '') or ''
                if iid and iid not in seen_instance:
                    seen_instance.add(iid)
                    instance_ids.append(Safe_Str__EC2__Instance_Id(iid))
            sg.attached_eni_ids      = eni_ids
            sg.attached_instance_ids = instance_ids
            return sg
        except ClientError as exc:
            code = exc.response.get('Error', {}).get('Code', '')
            if code in ('InvalidGroup.NotFound', 'InvalidGroupId.Malformed'):
                return None
            raise

    def list_network_interfaces(self, sg_id: str = '') -> list:                # Returns raw ENI dicts filtered by Groups.GroupId == sg_id
        ec2     = self.client()
        filters = []
        if sg_id:
            filters.append({'Name': 'group-id', 'Values': [sg_id]})
        kwargs    = {'Filters': filters} if filters else {}
        result    = []
        paginator = ec2.get_paginator('describe_network_interfaces')
        for page in paginator.paginate(**kwargs):
            for raw in page.get('NetworkInterfaces', []) or []:
                result.append(raw)
        return result

    # ── mutations ─────────────────────────────────────────────────────────────

    def create_instance(self, request: Schema__EC2__Create__Request,
                        extra_tags: Optional[list] = None) -> Optional[str]:   # Returns new instance_id or None
        ec2   = self.client()
        tags  = [{'Key': 'Name', 'Value': str(request.name)}] if str(request.name) else []
        if extra_tags:
            tags.extend(extra_tags)
        kwargs = dict(
            ImageId      = str(request.ami_id),
            InstanceType = str(request.instance_type),
            MinCount     = 1,
            MaxCount     = 1,
        )
        if str(request.key_pair):
            kwargs['KeyName'] = str(request.key_pair)
        if str(request.subnet_id):
            kwargs['SubnetId'] = str(request.subnet_id)
        if str(request.security_groups):
            kwargs['SecurityGroupIds'] = [s.strip() for s in str(request.security_groups).split(',') if s.strip()]
        if str(request.user_data):
            kwargs['UserData'] = str(request.user_data)
        if tags:
            kwargs['TagSpecifications'] = [{'ResourceType': 'instance', 'Tags': tags}]
        resp      = ec2.run_instances(**kwargs)
        instances = resp.get('Instances', [])
        if not instances:
            return None
        return instances[0].get('InstanceId')

    def start_instance(self, instance_id: str) -> None:
        self.client().start_instances(InstanceIds=[instance_id])

    def stop_instance(self, instance_id: str) -> None:
        self.client().stop_instances(InstanceIds=[instance_id])

    def terminate_instance(self, instance_id: str) -> None:
        self.client().terminate_instances(InstanceIds=[instance_id])

    def deregister_image(self, ami_id: str) -> bool:                           # Returns True on success; False if AMI already gone
        try:
            self.client().deregister_image(ImageId=ami_id)
            return True
        except ClientError as exc:
            code = exc.response.get('Error', {}).get('Code', '')
            if code in ('InvalidAMIID.NotFound', 'InvalidAMIID.Unavailable'):
                return False
            raise

    def delete_snapshot(self, snapshot_id: str) -> bool:                       # Returns True on success; False if already gone
        try:
            self.client().delete_snapshot(SnapshotId=snapshot_id)
            return True
        except ClientError as exc:
            code = exc.response.get('Error', {}).get('Code', '')
            if code == 'InvalidSnapshot.NotFound':
                return False
            # InvalidSnapshot.InUse / others propagate so caller can show why
            raise

    def delete_security_group(self, sg_id_or_name: str, vpc_id: str = '') -> bool:
        # Resolve to a concrete sg_id first — supports name-based input and
        # surfaces NotFound as False before the mutation call.
        try:
            sg = self.describe_security_group(sg_id_or_name, vpc_id=vpc_id)
        except ClientError as exc:
            code = exc.response.get('Error', {}).get('Code', '')
            if code in ('InvalidGroup.NotFound', 'InvalidGroupId.Malformed'):
                return False
            raise
        if sg is None:
            return False
        try:
            self.client().delete_security_group(GroupId=str(sg.sg_id))
            return True
        except ClientError as exc:
            code = exc.response.get('Error', {}).get('Code', '')
            if code in ('InvalidGroup.NotFound', 'InvalidGroupId.Malformed'):
                return False
            # DependencyViolation and any other ClientError re-raise so the
            # user sees the real AWS reason via @spec_cli_errors.
            raise

    def add_tags(self, instance_id: str, tags: dict) -> None:                  # tags is {Key: Value} map
        self.client().create_tags(
            Resources = [instance_id],
            Tags      = [{'Key': k, 'Value': v} for k, v in tags.items()],
        )

    def remove_tags(self, instance_id: str, keys: list) -> None:
        self.client().delete_tags(
            Resources = [instance_id],
            Tags      = [{'Key': k} for k in keys],
        )

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
        tags_dict = Dict__EC2__Tag()
        for k, v in tags.items():
            tags_dict[k] = v

        sgs_list = List__Schema__EC2__Security_Group__Ref()
        for sg_raw in raw.get('SecurityGroups', []):
            sgs_list.append(Schema__EC2__Security_Group__Ref(
                group_id   = sg_raw.get('GroupId', ''),
                group_name = sg_raw.get('GroupName', ''),
            ))

        bdm_list = List__Schema__EC2__Block_Device__Mapping()
        for bdm in raw.get('BlockDeviceMappings', []):
            ebs = bdm.get('Ebs', {})
            bdm_list.append(Schema__EC2__Block_Device__Mapping(
                device_name           = bdm.get('DeviceName', ''),
                volume_id             = ebs.get('VolumeId', ''),
                volume_size           = ebs.get('VolumeSize', 0),
                delete_on_termination = bool(ebs.get('DeleteOnTermination', True)),
                status                = ebs.get('Status', ''),
            ))

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
            platform             = raw.get('Platform', '')         or '',
            iam_instance_profile = iam_profile,
            root_device_type     = raw.get('RootDeviceType', '')   or '',
            tags                 = tags_dict,
            security_groups      = sgs_list,
            block_devices        = bdm_list,
        )

    def _parse_ami(self, raw: dict) -> Schema__EC2__AMI:
        ami_id    = raw.get('ImageId', '')            or ''
        name      = raw.get('Name', '')               or ''
        desc      = raw.get('Description', '')        or ''
        owner_id  = raw.get('OwnerId', '')            or ''
        created   = raw.get('CreationDate', '')       or ''                     # ISO-8601 string
        public    = bool(raw.get('Public', False))
        arch      = raw.get('Architecture', '')       or ''
        root_type = raw.get('RootDeviceType', '')     or ''
        snap_ids  = []
        for bdm in raw.get('BlockDeviceMappings', []) or []:
            ebs    = bdm.get('Ebs') or {}
            snap_s = ebs.get('SnapshotId', '') or ''
            if snap_s:
                snap_ids.append(Safe_Str__EC2__Snapshot_Id(snap_s))
        return Schema__EC2__AMI(
            ami_id                = Safe_Str__EC2__AMI_Id(ami_id) if ami_id else Safe_Str__EC2__AMI_Id(''),
            name                  = name,
            description           = desc,
            owner_id              = owner_id,
            created_at            = created,
            public                = public,
            architecture          = arch,
            root_device_type      = root_type,
            snapshot_ids          = snap_ids,
            attached_instance_ids = [],
        )

    def _parse_security_group(self, raw: dict) -> Schema__EC2__Security_Group:
        sg_id    = raw.get('GroupId', '')     or ''
        name     = raw.get('GroupName', '')   or ''
        vpc_id   = raw.get('VpcId', '')       or ''
        desc     = raw.get('Description', '') or ''
        owner_id = raw.get('OwnerId', '')     or ''
        ingress  = self._parse_sg_rules(raw.get('IpPermissions', [])       or [],
                                        Enum__EC2__SG_Rule_Direction.INGRESS)
        egress   = self._parse_sg_rules(raw.get('IpPermissionsEgress', []) or [],
                                        Enum__EC2__SG_Rule_Direction.EGRESS)
        return Schema__EC2__Security_Group(
            sg_id                 = Safe_Str__EC2__SG_Id(sg_id),
            name                  = name,
            vpc_id                = Safe_Str__EC2__VPC_Id(vpc_id),
            description           = desc,
            owner_id              = owner_id,
            ingress_rules         = ingress,
            egress_rules          = egress,
            attached_eni_ids      = [],
            attached_instance_ids = [],
        )

    def _parse_sg_rules(self, perms: list, direction: Enum__EC2__SG_Rule_Direction
                        ) -> List__Schema__EC2__SG_Rule:
        rules = List__Schema__EC2__SG_Rule()
        for perm in perms:
            proto     = perm.get('IpProtocol', '') or ''
            from_port = int(perm.get('FromPort', -1)) if perm.get('FromPort') is not None else -1
            to_port   = int(perm.get('ToPort', -1))   if perm.get('ToPort')   is not None else -1
            # ── expand per-target rows (one row per cidr-ipv4 / cidr-ipv6 / referenced SG) ──
            for r in perm.get('IpRanges', []) or []:
                rules.append(Schema__EC2__SG_Rule(
                    ip_protocol      = proto,
                    from_port        = from_port,
                    to_port          = to_port,
                    direction        = direction,
                    cidr_ipv4        = r.get('CidrIp', '')      or '',
                    cidr_ipv6        = '',
                    referenced_sg_id = Safe_Str__EC2__SG_Id(''),
                    description      = r.get('Description', '') or '',
                ))
            for r in perm.get('Ipv6Ranges', []) or []:
                rules.append(Schema__EC2__SG_Rule(
                    ip_protocol      = proto,
                    from_port        = from_port,
                    to_port          = to_port,
                    direction        = direction,
                    cidr_ipv4        = '',
                    cidr_ipv6        = r.get('CidrIpv6', '')    or '',
                    referenced_sg_id = Safe_Str__EC2__SG_Id(''),
                    description      = r.get('Description', '') or '',
                ))
            for r in perm.get('UserIdGroupPairs', []) or []:
                ref_id = r.get('GroupId', '') or ''
                rules.append(Schema__EC2__SG_Rule(
                    ip_protocol      = proto,
                    from_port        = from_port,
                    to_port          = to_port,
                    direction        = direction,
                    cidr_ipv4        = '',
                    cidr_ipv6        = '',
                    referenced_sg_id = Safe_Str__EC2__SG_Id(ref_id),
                    description      = r.get('Description', '') or '',
                ))
            # ── perm with no targets (degenerate) — still emit one row so caller sees the rule ──
            if (not perm.get('IpRanges') and not perm.get('Ipv6Ranges')
                    and not perm.get('UserIdGroupPairs')):
                rules.append(Schema__EC2__SG_Rule(
                    ip_protocol      = proto,
                    from_port        = from_port,
                    to_port          = to_port,
                    direction        = direction,
                    cidr_ipv4        = '',
                    cidr_ipv6        = '',
                    referenced_sg_id = Safe_Str__EC2__SG_Id(''),
                    description      = '',
                ))
        return rules

    def _parse_snapshot(self, raw: dict) -> Schema__EC2__Snapshot:
        snap_id   = raw.get('SnapshotId', '')   or ''
        vol_id    = raw.get('VolumeId', '')     or ''
        vol_size  = int(raw.get('VolumeSize', 0) or 0)
        desc      = raw.get('Description', '')  or ''
        state     = raw.get('State', '')        or ''
        started   = raw.get('StartTime', '')
        started_s = str(started) if started else ''
        owner_id  = raw.get('OwnerId', '')      or ''
        return Schema__EC2__Snapshot(
            snapshot_id     = Safe_Str__EC2__Snapshot_Id(snap_id) if snap_id else Safe_Str__EC2__Snapshot_Id(''),
            volume_id       = vol_id,
            volume_size_gib = vol_size,
            description     = desc,
            state           = state,
            started_at      = started_s,
            owner_id        = owner_id,
        )
