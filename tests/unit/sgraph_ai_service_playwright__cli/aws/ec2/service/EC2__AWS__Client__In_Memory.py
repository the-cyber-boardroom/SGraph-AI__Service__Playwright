# ═══════════════════════════════════════════════════════════════════════════════
# Tests — EC2__AWS__Client__In_Memory
# Dict-backed fake boto3 EC2 client for unit tests. No mocks. No patches.
# Supports describe_instances, run_instances, start/stop/terminate, tags,
# describe_images (AMI list/show) and describe_snapshots.
# ═══════════════════════════════════════════════════════════════════════════════

import secrets
from datetime import datetime, timezone

from botocore.exceptions import ClientError

from sgraph_ai_service_playwright__cli.aws.ec2.service.EC2__AWS__Client import EC2__AWS__Client


class _Fake_EC2_Client:                                                        # Minimal boto3-alike EC2 client backed by in-memory dicts

    def __init__(self, store: dict, images_store: dict = None,
                 snapshots_store: dict = None,
                 security_groups_store: dict = None,
                 network_interfaces_store: dict = None):
        self._store                    = store                                  # instance_id → raw instance dict
        self._images_store             = images_store             if images_store             is not None else {}
        self._snapshots_store          = snapshots_store          if snapshots_store          is not None else {}
        self._security_groups_store    = security_groups_store    if security_groups_store    is not None else {}
        self._network_interfaces_store = network_interfaces_store if network_interfaces_store is not None else {}

    # ── paginator ─────────────────────────────────────────────────────────────

    def get_paginator(self, method: str):
        return _Fake_Paginator(self, method)

    # ── describe_instances ────────────────────────────────────────────────────

    def describe_instances(self, InstanceIds=None, Filters=None):
        instances = list(self._store.values())
        if InstanceIds:
            instances = [i for i in instances if i['InstanceId'] in InstanceIds]
        if Filters:
            instances = self._apply_filters(instances, Filters)
        return {'Reservations': [{'Instances': [i]} for i in instances]}

    # ── run_instances ─────────────────────────────────────────────────────────

    def run_instances(self, ImageId='', InstanceType='', MinCount=1, MaxCount=1,
                      KeyName='', SubnetId='', SecurityGroupIds=None, UserData='',
                      TagSpecifications=None, **_):
        iid   = f'i-{secrets.token_hex(8)}'
        tags  = []
        if TagSpecifications:
            for ts in TagSpecifications:
                tags.extend(ts.get('Tags', []))
        raw   = {
            'InstanceId'          : iid,
            'InstanceType'        : InstanceType,
            'ImageId'             : ImageId,
            'State'               : {'Name': 'pending', 'Code': 0},
            'PublicIpAddress'     : '',
            'PublicDnsName'       : '',
            'PrivateIpAddress'    : '10.0.0.1',
            'PrivateDnsName'      : 'ip-10-0-0-1.ec2.internal',
            'LaunchTime'          : datetime.now(timezone.utc),
            'KeyName'             : KeyName,
            'VpcId'               : 'vpc-00000000',
            'SubnetId'            : SubnetId or 'subnet-00000000',
            'Architecture'        : 'x86_64',
            'Platform'            : '',
            'IamInstanceProfile'  : None,
            'RootDeviceType'      : 'ebs',
            'Tags'                : tags,
            'SecurityGroups'      : [{'GroupId': sg, 'GroupName': sg} for sg in (SecurityGroupIds or [])],
            'BlockDeviceMappings' : [],
        }
        self._store[iid] = raw
        return {'Instances': [raw]}

    # ── start / stop / terminate ──────────────────────────────────────────────

    def start_instances(self, InstanceIds=None):
        for iid in (InstanceIds or []):
            if iid in self._store:
                self._store[iid]['State'] = {'Name': 'running', 'Code': 16}
        return {'StartingInstances': []}

    def stop_instances(self, InstanceIds=None):
        for iid in (InstanceIds or []):
            if iid in self._store:
                self._store[iid]['State'] = {'Name': 'stopped', 'Code': 80}
        return {'StoppingInstances': []}

    def terminate_instances(self, InstanceIds=None):
        for iid in (InstanceIds or []):
            if iid in self._store:
                self._store[iid]['State'] = {'Name': 'terminated', 'Code': 48}
        return {'TerminatingInstances': []}

    # ── tags ──────────────────────────────────────────────────────────────────

    def describe_tags(self, Filters=None):
        resource_ids = []
        if Filters:
            for f in Filters:
                if f.get('Name') == 'resource-id':
                    resource_ids = f.get('Values', [])
        tags = []
        for iid in resource_ids:
            if iid in self._store:
                for tag in self._store[iid].get('Tags', []):
                    tags.append(dict(ResourceId=iid, ResourceType='instance',
                                     Key=tag['Key'], Value=tag['Value']))
        return {'Tags': tags}

    def create_tags(self, Resources=None, Tags=None):
        for iid in (Resources or []):
            if iid in self._store:
                existing = {t['Key']: i for i, t in enumerate(self._store[iid].get('Tags', []))}
                for tag in (Tags or []):
                    k, v = tag.get('Key', ''), tag.get('Value', '')
                    if k in existing:
                        self._store[iid]['Tags'][existing[k]] = {'Key': k, 'Value': v}
                    else:
                        self._store[iid].setdefault('Tags', []).append({'Key': k, 'Value': v})

    def delete_tags(self, Resources=None, Tags=None):
        keys = {t.get('Key') for t in (Tags or [])}
        for iid in (Resources or []):
            if iid in self._store:
                self._store[iid]['Tags'] = [t for t in self._store[iid].get('Tags', [])
                                             if t.get('Key') not in keys]

    # ── instance types ────────────────────────────────────────────────────────

    def describe_instance_types(self, Filters=None):                           # Returns fixed small list for tests; applies family filter if present
        all_types = [
            {'InstanceType': 't3.nano'},
            {'InstanceType': 't3.micro'},
            {'InstanceType': 't3.small'},
            {'InstanceType': 'm5.large'},
        ]
        if not Filters:
            return {'InstanceTypes': all_types}
        filtered = all_types
        for f in (Filters or []):
            if f.get('Name') == 'instance-type':
                patterns = f.get('Values', [])
                result   = []
                for itype_dict in filtered:
                    itype = itype_dict['InstanceType']
                    for p in patterns:
                        if p.endswith('.*'):
                            prefix = p[:-2]
                            if itype.startswith(prefix + '.'):
                                result.append(itype_dict)
                                break
                        elif itype == p:
                            result.append(itype_dict)
                            break
                filtered = result
        return {'InstanceTypes': filtered}

    # ── describe_images (AMIs) ────────────────────────────────────────────────

    def describe_images(self, ImageIds=None, Owners=None, Filters=None):
        images = list(self._images_store.values())
        if ImageIds:
            matched = [i for i in images if i.get('ImageId', '') in ImageIds]
            missing = [i for i in ImageIds if i not in self._images_store]
            if not matched and missing:                                          # mirror real EC2: unknown ID raises ClientError
                raise ClientError(
                    {'Error': {'Code': 'InvalidAMIID.NotFound',
                                'Message': f'The image id {missing} does not exist'}},
                    'DescribeImages')
            images = matched
        if Owners:                                                               # Owners is matched literally; seed_ami uses 'self'/'amazon' as the owner string
            images = [i for i in images if i.get('OwnerId', '') in Owners]
        if Filters:
            images = self._apply_image_filters(images, Filters)
        return {'Images': images}

    def _apply_image_filters(self, images: list, filters: list) -> list:
        result = images
        for f in filters:
            name   = f.get('Name', '')
            values = f.get('Values', [])
            if name == 'name':
                kept = []
                for img in result:
                    img_name = img.get('Name', '') or ''
                    for v in values:
                        if v.startswith('*') and v.endswith('*'):                 # substring match
                            needle = v[1:-1]
                            if needle in img_name:
                                kept.append(img); break
                        elif v.startswith('*'):
                            if img_name.endswith(v[1:]):
                                kept.append(img); break
                        elif v.endswith('*'):
                            if img_name.startswith(v[:-1]):
                                kept.append(img); break
                        else:
                            if img_name == v:
                                kept.append(img); break
                result = kept
        return result

    # ── deregister_image ──────────────────────────────────────────────────────

    def deregister_image(self, ImageId=''):
        if ImageId not in self._images_store:
            raise ClientError(
                {'Error': {'Code': 'InvalidAMIID.NotFound',
                            'Message': f'The image id {ImageId} does not exist'}},
                'DeregisterImage')
        del self._images_store[ImageId]
        return {}

    # ── delete_snapshot ───────────────────────────────────────────────────────

    def delete_snapshot(self, SnapshotId=''):
        if SnapshotId not in self._snapshots_store:
            raise ClientError(
                {'Error': {'Code': 'InvalidSnapshot.NotFound',
                            'Message': f'The snapshot {SnapshotId} does not exist'}},
                'DeleteSnapshot')
        raw = self._snapshots_store[SnapshotId]
        if raw.get('_InUse'):
            raise ClientError(
                {'Error': {'Code': 'InvalidSnapshot.InUse',
                            'Message': f'The snapshot {SnapshotId} is currently in use'}},
                'DeleteSnapshot')
        del self._snapshots_store[SnapshotId]
        return {}

    # ── describe_security_groups ──────────────────────────────────────────────

    def describe_security_groups(self, GroupIds=None, Filters=None):
        groups = list(self._security_groups_store.values())
        if GroupIds:
            matched = [g for g in groups if g.get('GroupId', '') in GroupIds]
            missing = [i for i in GroupIds if i not in self._security_groups_store]
            if not matched and missing:                                          # mirror real EC2: unknown ID raises ClientError
                raise ClientError(
                    {'Error': {'Code': 'InvalidGroup.NotFound',
                                'Message': f'The security group {missing} does not exist'}},
                    'DescribeSecurityGroups')
            groups = matched
        if Filters:
            groups = self._apply_sg_filters(groups, Filters)
        return {'SecurityGroups': groups}

    def _apply_sg_filters(self, groups: list, filters: list) -> list:
        result = groups
        for f in filters:
            name   = f.get('Name', '')
            values = f.get('Values', [])
            if name == 'vpc-id':
                result = [g for g in result if g.get('VpcId', '') in values]
            elif name == 'group-name':
                kept = []
                for g in result:
                    gname = g.get('GroupName', '') or ''
                    for v in values:
                        if v.startswith('*') and v.endswith('*'):                # substring match
                            needle = v[1:-1]
                            if needle in gname:
                                kept.append(g); break
                        elif v.startswith('*'):
                            if gname.endswith(v[1:]):
                                kept.append(g); break
                        elif v.endswith('*'):
                            if gname.startswith(v[:-1]):
                                kept.append(g); break
                        else:
                            if gname == v:
                                kept.append(g); break
                result = kept
        return result

    # ── delete_security_group ─────────────────────────────────────────────────

    def delete_security_group(self, GroupId='', GroupName=''):
        target = GroupId or GroupName
        if target not in self._security_groups_store:
            raise ClientError(
                {'Error': {'Code': 'InvalidGroup.NotFound',
                            'Message': f'The security group {target} does not exist'}},
                'DeleteSecurityGroup')
        # mirror AWS: any ENI still using this SG → DependencyViolation
        for eni in self._network_interfaces_store.values():
            for g in (eni.get('Groups', []) or []):
                if g.get('GroupId', '') == target:
                    raise ClientError(
                        {'Error': {'Code': 'DependencyViolation',
                                    'Message': f'resource {target} has a dependent object'}},
                        'DeleteSecurityGroup')
        del self._security_groups_store[target]
        return {}

    # ── describe_network_interfaces ───────────────────────────────────────────

    def describe_network_interfaces(self, Filters=None):
        enis = list(self._network_interfaces_store.values())
        if Filters:
            for f in Filters:
                name   = f.get('Name', '')
                values = f.get('Values', [])
                if name == 'group-id':
                    enis = [e for e in enis
                            if any(g.get('GroupId', '') in values
                                   for g in (e.get('Groups', []) or []))]
                elif name == 'vpc-id':
                    enis = [e for e in enis if e.get('VpcId', '') in values]
        return {'NetworkInterfaces': enis}

    # ── describe_snapshots ────────────────────────────────────────────────────

    def describe_snapshots(self, SnapshotIds=None, OwnerIds=None, Filters=None):
        snaps = list(self._snapshots_store.values())
        if SnapshotIds:
            snaps = [s for s in snaps if s.get('SnapshotId', '') in SnapshotIds]
        if OwnerIds:                                                             # OwnerIds matched literally; seed_snapshot uses 'self'/'amazon' as the owner string
            snaps = [s for s in snaps if s.get('OwnerId', '') in OwnerIds]
        return {'Snapshots': snaps}

    # ── internal ──────────────────────────────────────────────────────────────

    def _apply_filters(self, instances: list, filters: list) -> list:
        result = instances
        for f in filters:
            name   = f.get('Name', '')
            values = f.get('Values', [])
            if name == 'instance-state-name':
                result = [i for i in result if i['State']['Name'] in values]
            elif name.startswith('tag:'):
                key = name[4:]
                result = [i for i in result
                          if any(t.get('Key') == key and
                                 any(t.get('Value', '') == v or v.endswith('*') and
                                     t.get('Value', '').startswith(v[:-1])
                                     for v in values)
                                 for t in i.get('Tags', []))]
        return result


class _Fake_Paginator:
    def __init__(self, client: _Fake_EC2_Client, method: str):
        self._client = client
        self._method = method

    def paginate(self, **kwargs):
        if self._method == 'describe_instances':
            yield self._client.describe_instances(Filters=kwargs.get('Filters'))
        elif self._method == 'describe_instance_types':
            yield self._client.describe_instance_types(Filters=kwargs.get('Filters'))
        elif self._method == 'describe_images':
            yield self._client.describe_images(ImageIds=kwargs.get('ImageIds'),
                                                Owners  =kwargs.get('Owners'),
                                                Filters =kwargs.get('Filters'))
        elif self._method == 'describe_snapshots':
            yield self._client.describe_snapshots(SnapshotIds=kwargs.get('SnapshotIds'),
                                                   OwnerIds   =kwargs.get('OwnerIds'),
                                                   Filters    =kwargs.get('Filters'))
        elif self._method == 'describe_security_groups':
            yield self._client.describe_security_groups(GroupIds=kwargs.get('GroupIds'),
                                                        Filters =kwargs.get('Filters'))
        elif self._method == 'describe_network_interfaces':
            yield self._client.describe_network_interfaces(Filters=kwargs.get('Filters'))


class EC2__AWS__Client__In_Memory(EC2__AWS__Client):

    def __init__(self):
        super().__init__()
        self._store                    = {}
        self._images_store             = {}
        self._snapshots_store          = {}
        self._security_groups_store    = {}
        self._network_interfaces_store = {}
        self._fake                     = _Fake_EC2_Client(
            self._store,
            images_store             = self._images_store,
            snapshots_store          = self._snapshots_store,
            security_groups_store    = self._security_groups_store,
            network_interfaces_store = self._network_interfaces_store,
        )

    def client(self):
        return self._fake

    # ── seed: AMIs ────────────────────────────────────────────────────────────

    def seed_ami(self, ami_id: str = '', name: str = '',
                 owner: str = '123456789012',
                 created: str = '2026-04-01T00:00:00.000Z',
                 description: str = '',
                 architecture: str = 'x86_64',
                 root_device_type: str = 'ebs',
                 snapshot_ids: list = None,
                 public: bool = False) -> str:
        if not ami_id:
            ami_id = f'ami-{secrets.token_hex(8)}'
        bdms = []
        for snap in (snapshot_ids or []):
            bdms.append({'DeviceName': '/dev/xvda',
                         'Ebs'       : {'SnapshotId': snap, 'VolumeSize': 8}})
        raw = {
            'ImageId'             : ami_id,
            'Name'                : name,
            'Description'         : description,
            'OwnerId'             : owner,
            'CreationDate'        : created,
            'Public'              : public,
            'Architecture'        : architecture,
            'RootDeviceType'      : root_device_type,
            'BlockDeviceMappings' : bdms,
        }
        self._images_store[ami_id] = raw
        return ami_id

    # ── seed: snapshots ───────────────────────────────────────────────────────

    def seed_snapshot(self, snapshot_id: str = '',
                      volume_id: str = '',
                      size_gib: int = 8,
                      description: str = '',
                      state: str = 'completed',
                      owner: str = '123456789012',
                      started: str = '2026-04-01T00:00:00.000Z',
                      in_use: bool = False) -> str:
        if not snapshot_id:
            snapshot_id = f'snap-{secrets.token_hex(8)}'
        if not volume_id:
            volume_id = f'vol-{secrets.token_hex(8)}'
        raw = {
            'SnapshotId'  : snapshot_id,
            'VolumeId'    : volume_id,
            'VolumeSize'  : size_gib,
            'Description' : description,
            'State'       : state,
            'StartTime'   : started,
            'OwnerId'     : owner,
            '_InUse'      : in_use,                                              # in-memory only: drives delete_snapshot → InvalidSnapshot.InUse
        }
        self._snapshots_store[snapshot_id] = raw
        return snapshot_id

    def seed_instance(self, instance_id: str = '', name: str = '',
                      state: str = 'running', instance_type: str = 't3.micro',
                      ami_id: str = 'ami-12345678', public_ip: str = '',
                      key_name: str = 'my-key') -> str:
        if not instance_id:
            instance_id = f'i-{secrets.token_hex(8)}'
        tags = [{'Key': 'Name', 'Value': name}] if name else []
        self._store[instance_id] = {
            'InstanceId'          : instance_id,
            'InstanceType'        : instance_type,
            'ImageId'             : ami_id,
            'State'               : {'Name': state, 'Code': 16 if state == 'running' else 80},
            'PublicIpAddress'     : public_ip or '',
            'PublicDnsName'       : f'ec2-1-2-3-4.compute-1.amazonaws.com' if public_ip else '',
            'PrivateIpAddress'    : '10.0.0.1',
            'PrivateDnsName'      : 'ip-10-0-0-1.ec2.internal',
            'LaunchTime'          : datetime.now(timezone.utc),
            'KeyName'             : key_name,
            'VpcId'               : 'vpc-00000000',
            'SubnetId'            : 'subnet-00000000',
            'Architecture'        : 'x86_64',
            'Platform'            : '',
            'IamInstanceProfile'  : None,
            'RootDeviceType'      : 'ebs',
            'Tags'                : tags,
            'SecurityGroups'      : [],
            'BlockDeviceMappings' : [],
        }
        return instance_id

    # ── seed: security groups ─────────────────────────────────────────────────

    def seed_security_group(self, sg_id: str = '', name: str = '',
                            vpc_id: str = 'vpc-default',
                            description: str = '',
                            owner_id: str = '123456789012',
                            ingress: list = None,
                            egress: list = None) -> str:
        if not sg_id:
            sg_id = f'sg-{secrets.token_hex(8)}'
        raw = {
            'GroupId'            : sg_id,
            'GroupName'          : name,
            'VpcId'              : vpc_id,
            'Description'        : description,
            'OwnerId'            : owner_id,
            'IpPermissions'      : ingress or [],
            'IpPermissionsEgress': egress  or [],
        }
        self._security_groups_store[sg_id] = raw
        return sg_id

    # ── seed: network interfaces ──────────────────────────────────────────────

    def seed_network_interface(self, eni_id: str = '',
                               sg_ids: list = None,
                               instance_id: str = '',
                               vpc_id: str = 'vpc-default') -> str:
        if not eni_id:
            eni_id = f'eni-{secrets.token_hex(8)}'
        groups = [{'GroupId': g, 'GroupName': g} for g in (sg_ids or [])]
        raw = {
            'NetworkInterfaceId': eni_id,
            'VpcId'             : vpc_id,
            'Groups'            : groups,
        }
        if instance_id:
            raw['Attachment'] = {'InstanceId': instance_id}
        self._network_interfaces_store[eni_id] = raw
        return eni_id
