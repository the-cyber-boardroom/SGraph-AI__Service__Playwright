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
                 network_interfaces_store: dict = None,
                 vpcs_store: dict = None,
                 subnets_store: dict = None,
                 internet_gateways_store: dict = None,
                 route_tables_store: dict = None,
                 counters: dict = None):
        self._store                    = store                                  # instance_id → raw instance dict
        self._images_store             = images_store             if images_store             is not None else {}
        self._snapshots_store          = snapshots_store          if snapshots_store          is not None else {}
        self._security_groups_store    = security_groups_store    if security_groups_store    is not None else {}
        self._network_interfaces_store = network_interfaces_store if network_interfaces_store is not None else {}
        self._vpcs_store               = vpcs_store               if vpcs_store               is not None else {}
        self._subnets_store            = subnets_store            if subnets_store            is not None else {}
        self._internet_gateways_store  = internet_gateways_store  if internet_gateways_store  is not None else {}
        self._route_tables_store       = route_tables_store       if route_tables_store       is not None else {}
        self._counters                 = counters                 if counters                 is not None else {}

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

    def describe_network_interfaces(self, NetworkInterfaceIds=None, Filters=None):
        enis = list(self._network_interfaces_store.values())
        if NetworkInterfaceIds:
            matched = [e for e in enis
                       if e.get('NetworkInterfaceId', '') in NetworkInterfaceIds]
            missing = [i for i in NetworkInterfaceIds
                       if i not in self._network_interfaces_store]
            if not matched and missing:
                raise ClientError(
                    {'Error': {'Code': 'InvalidNetworkInterfaceID.NotFound',
                                'Message': f'The network interface {missing} does not exist'}},
                    'DescribeNetworkInterfaces')
            enis = matched
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

    # ── describe_vpcs ─────────────────────────────────────────────────────────

    def describe_vpcs(self, VpcIds=None, Filters=None):
        vpcs = list(self._vpcs_store.values())
        if VpcIds:
            matched = [v for v in vpcs if v.get('VpcId', '') in VpcIds]
            missing = [i for i in VpcIds if i not in self._vpcs_store]
            if not matched and missing:
                raise ClientError(
                    {'Error': {'Code': 'InvalidVpcID.NotFound',
                                'Message': f'The vpc id {missing} does not exist'}},
                    'DescribeVpcs')
            vpcs = matched
        if Filters:
            vpcs = self._apply_tag_filters(vpcs, Filters)
        return {'Vpcs': vpcs}

    # ── describe_subnets ──────────────────────────────────────────────────────

    def describe_subnets(self, SubnetIds=None, Filters=None):
        subs = list(self._subnets_store.values())
        if SubnetIds:
            matched = [s for s in subs if s.get('SubnetId', '') in SubnetIds]
            missing = [i for i in SubnetIds if i not in self._subnets_store]
            if not matched and missing:
                raise ClientError(
                    {'Error': {'Code': 'InvalidSubnetID.NotFound',
                                'Message': f'The subnet id {missing} does not exist'}},
                    'DescribeSubnets')
            subs = matched
        if Filters:
            for f in Filters:
                name   = f.get('Name', '')
                values = f.get('Values', [])
                if name == 'vpc-id':
                    subs = [s for s in subs if s.get('VpcId', '') in values]
                elif name == 'availability-zone':
                    subs = [s for s in subs
                            if s.get('AvailabilityZone', '') in values]
                elif name.startswith('tag:'):
                    subs = self._apply_tag_filters(subs, [f])
        return {'Subnets': subs}

    # ── describe_internet_gateways ────────────────────────────────────────────

    def describe_internet_gateways(self, InternetGatewayIds=None, Filters=None):
        igws = list(self._internet_gateways_store.values())
        if InternetGatewayIds:
            matched = [i for i in igws
                       if i.get('InternetGatewayId', '') in InternetGatewayIds]
            missing = [x for x in InternetGatewayIds
                       if x not in self._internet_gateways_store]
            if not matched and missing:
                raise ClientError(
                    {'Error': {'Code': 'InvalidInternetGatewayID.NotFound',
                                'Message': f'The igw id {missing} does not exist'}},
                    'DescribeInternetGateways')
            igws = matched
        if Filters:
            for f in Filters:
                name   = f.get('Name', '')
                values = f.get('Values', [])
                if name == 'attachment.vpc-id':
                    igws = [i for i in igws
                            if any(a.get('VpcId', '') in values
                                   for a in (i.get('Attachments', []) or []))]
                elif name.startswith('tag:'):
                    igws = self._apply_tag_filters(igws, [f])
        return {'InternetGateways': igws}

    # ── describe_route_tables ─────────────────────────────────────────────────

    def describe_route_tables(self, RouteTableIds=None, Filters=None):
        rtbs = list(self._route_tables_store.values())
        if RouteTableIds:
            matched = [r for r in rtbs
                       if r.get('RouteTableId', '') in RouteTableIds]
            missing = [x for x in RouteTableIds
                       if x not in self._route_tables_store]
            if not matched and missing:
                raise ClientError(
                    {'Error': {'Code': 'InvalidRouteTableID.NotFound',
                                'Message': f'The route table id {missing} does not exist'}},
                    'DescribeRouteTables')
            rtbs = matched
        if Filters:
            for f in Filters:
                name   = f.get('Name', '')
                values = f.get('Values', [])
                if name == 'vpc-id':
                    rtbs = [r for r in rtbs if r.get('VpcId', '') in values]
                elif name.startswith('tag:'):
                    rtbs = self._apply_tag_filters(rtbs, [f])
        return {'RouteTables': rtbs}

    # ── mutations: VPC ────────────────────────────────────────────────────────

    def create_vpc(self, CidrBlock='', TagSpecifications=None, **_):
        vpc_id   = self._next_id('vpc')
        raw_tags = self._tags_from_specs(TagSpecifications, 'vpc')
        raw = {
            'VpcId'           : vpc_id,
            'CidrBlock'       : CidrBlock,
            'IsDefault'       : False,
            'State'           : 'available',
            'DhcpOptionsId'   : 'dopt-default',
            'InstanceTenancy' : 'default',
            'Tags'            : raw_tags,
        }
        self._vpcs_store[vpc_id] = raw
        return {'Vpc': raw}

    def delete_vpc(self, VpcId=''):
        if VpcId not in self._vpcs_store:
            raise ClientError(
                {'Error': {'Code': 'InvalidVpcID.NotFound',
                            'Message': f'The vpc id {VpcId} does not exist'}},
                'DeleteVpc')
        del self._vpcs_store[VpcId]
        # Cascade: any subnets / IGWs / route tables that pointed here keep
        # their refs; AWS would have rejected deletion of a non-empty VPC, but
        # the in-memory fake mirrors the trusting interface so the unit tests
        # for the *client* can exercise both happy / sad paths independently.
        for igw in self._internet_gateways_store.values():
            igw['Attachments'] = [a for a in (igw.get('Attachments') or [])
                                   if a.get('VpcId') != VpcId]
        return {}

    def modify_vpc_attribute(self, VpcId='', EnableDnsSupport=None,
                              EnableDnsHostnames=None, **_):
        vpc = self._vpcs_store.get(VpcId)
        if vpc is None:
            raise ClientError(
                {'Error': {'Code': 'InvalidVpcID.NotFound',
                            'Message': f'The vpc id {VpcId} does not exist'}},
                'ModifyVpcAttribute')
        if EnableDnsSupport is not None:
            vpc['EnableDnsSupport']   = bool(EnableDnsSupport.get('Value', False))
        if EnableDnsHostnames is not None:
            vpc['EnableDnsHostnames'] = bool(EnableDnsHostnames.get('Value', False))
        return {}

    # ── mutations: Subnet ─────────────────────────────────────────────────────

    def create_subnet(self, VpcId='', CidrBlock='', AvailabilityZone='',
                      TagSpecifications=None, **_):
        if VpcId not in self._vpcs_store:
            raise ClientError(
                {'Error': {'Code': 'InvalidVpcID.NotFound',
                            'Message': f'The vpc id {VpcId} does not exist'}},
                'CreateSubnet')
        subnet_id = self._next_id('subnet')
        raw_tags  = self._tags_from_specs(TagSpecifications, 'subnet')
        raw = {
            'SubnetId'                : subnet_id,
            'VpcId'                   : VpcId,
            'CidrBlock'               : CidrBlock,
            'AvailabilityZone'        : AvailabilityZone or 'eu-west-2a',
            'AvailabilityZoneId'      : '',
            'AvailableIpAddressCount' : 251,
            'MapPublicIpOnLaunch'     : False,
            'State'                   : 'available',
            'Tags'                    : raw_tags,
        }
        self._subnets_store[subnet_id] = raw
        return {'Subnet': raw}

    def delete_subnet(self, SubnetId=''):
        if SubnetId not in self._subnets_store:
            raise ClientError(
                {'Error': {'Code': 'InvalidSubnetID.NotFound',
                            'Message': f'The subnet id {SubnetId} does not exist'}},
                'DeleteSubnet')
        del self._subnets_store[SubnetId]
        return {}

    def modify_subnet_attribute(self, SubnetId='', MapPublicIpOnLaunch=None, **_):
        sub = self._subnets_store.get(SubnetId)
        if sub is None:
            raise ClientError(
                {'Error': {'Code': 'InvalidSubnetID.NotFound',
                            'Message': f'The subnet id {SubnetId} does not exist'}},
                'ModifySubnetAttribute')
        if MapPublicIpOnLaunch is not None:
            sub['MapPublicIpOnLaunch'] = bool(MapPublicIpOnLaunch.get('Value', False))
        return {}

    # ── mutations: Internet Gateway ───────────────────────────────────────────

    def create_internet_gateway(self, TagSpecifications=None, **_):
        igw_id   = self._next_id('igw')
        raw_tags = self._tags_from_specs(TagSpecifications, 'internet-gateway')
        raw = {
            'InternetGatewayId' : igw_id,
            'Attachments'       : [],
            'Tags'              : raw_tags,
        }
        self._internet_gateways_store[igw_id] = raw
        return {'InternetGateway': raw}

    def delete_internet_gateway(self, InternetGatewayId=''):
        if InternetGatewayId not in self._internet_gateways_store:
            raise ClientError(
                {'Error': {'Code': 'InvalidInternetGatewayID.NotFound',
                            'Message': f'The igw id {InternetGatewayId} does not exist'}},
                'DeleteInternetGateway')
        del self._internet_gateways_store[InternetGatewayId]
        return {}

    def attach_internet_gateway(self, InternetGatewayId='', VpcId=''):
        igw = self._internet_gateways_store.get(InternetGatewayId)
        if igw is None:
            raise ClientError(
                {'Error': {'Code': 'InvalidInternetGatewayID.NotFound',
                            'Message': f'The igw id {InternetGatewayId} does not exist'}},
                'AttachInternetGateway')
        for a in (igw.get('Attachments') or []):
            if a.get('VpcId') == VpcId:
                raise ClientError(
                    {'Error': {'Code': 'Resource.AlreadyAssociated',
                                'Message': 'already attached'}},
                    'AttachInternetGateway')
        igw.setdefault('Attachments', []).append({'VpcId': VpcId, 'State': 'available'})
        return {}

    def detach_internet_gateway(self, InternetGatewayId='', VpcId=''):
        igw = self._internet_gateways_store.get(InternetGatewayId)
        if igw is None:
            raise ClientError(
                {'Error': {'Code': 'InvalidInternetGatewayID.NotFound',
                            'Message': f'The igw id {InternetGatewayId} does not exist'}},
                'DetachInternetGateway')
        attached = [a for a in (igw.get('Attachments') or []) if a.get('VpcId') == VpcId]
        if not attached:
            raise ClientError(
                {'Error': {'Code': 'Gateway.NotAttached',
                            'Message': 'not attached'}},
                'DetachInternetGateway')
        igw['Attachments'] = [a for a in (igw.get('Attachments') or [])
                               if a.get('VpcId') != VpcId]
        return {}

    # ── mutations: Route Table ────────────────────────────────────────────────

    def create_route_table(self, VpcId='', TagSpecifications=None, **_):
        if VpcId not in self._vpcs_store:
            raise ClientError(
                {'Error': {'Code': 'InvalidVpcID.NotFound',
                            'Message': f'The vpc id {VpcId} does not exist'}},
                'CreateRouteTable')
        rtb_id   = self._next_id('rtb')
        raw_tags = self._tags_from_specs(TagSpecifications, 'route-table')
        raw = {
            'RouteTableId' : rtb_id,
            'VpcId'        : VpcId,
            'Routes'       : [],
            'Associations' : [],
            'Tags'         : raw_tags,
        }
        self._route_tables_store[rtb_id] = raw
        return {'RouteTable': raw}

    def delete_route_table(self, RouteTableId=''):
        if RouteTableId not in self._route_tables_store:
            raise ClientError(
                {'Error': {'Code': 'InvalidRouteTableID.NotFound',
                            'Message': f'The route table id {RouteTableId} does not exist'}},
                'DeleteRouteTable')
        del self._route_tables_store[RouteTableId]
        return {}

    def associate_route_table(self, RouteTableId='', SubnetId=''):
        rtb = self._route_tables_store.get(RouteTableId)
        if rtb is None:
            raise ClientError(
                {'Error': {'Code': 'InvalidRouteTableID.NotFound',
                            'Message': f'The route table id {RouteTableId} does not exist'}},
                'AssociateRouteTable')
        assoc_id = self._next_id('rtbassoc')
        rtb.setdefault('Associations', []).append({
            'RouteTableAssociationId': assoc_id,
            'RouteTableId'           : RouteTableId,
            'SubnetId'               : SubnetId,
            'Main'                   : False,
        })
        return {'AssociationId': assoc_id}

    def disassociate_route_table(self, AssociationId=''):
        for rtb in self._route_tables_store.values():
            assocs = rtb.get('Associations', []) or []
            kept   = [a for a in assocs
                      if a.get('RouteTableAssociationId') != AssociationId]
            if len(kept) != len(assocs):
                rtb['Associations'] = kept
                return {}
        raise ClientError(
            {'Error': {'Code': 'InvalidAssociationID.NotFound',
                        'Message': f'The association {AssociationId} does not exist'}},
            'DisassociateRouteTable')

    def create_route(self, RouteTableId='', DestinationCidrBlock='',
                     GatewayId='', NatGatewayId='', NetworkInterfaceId='', **_):
        rtb = self._route_tables_store.get(RouteTableId)
        if rtb is None:
            raise ClientError(
                {'Error': {'Code': 'InvalidRouteTableID.NotFound',
                            'Message': f'The route table id {RouteTableId} does not exist'}},
                'CreateRoute')
        # Build the route row matching the boto3 shape the parser expects
        row = {'State': 'active', 'Origin': 'CreateRoute',
               'DestinationCidrBlock': DestinationCidrBlock}
        if GatewayId:
            row['GatewayId'] = GatewayId
        elif NatGatewayId:
            row['NatGatewayId'] = NatGatewayId
        elif NetworkInterfaceId:
            row['NetworkInterfaceId'] = NetworkInterfaceId
        rtb.setdefault('Routes', []).append(row)
        return {'Return': True}

    def delete_route(self, RouteTableId='', DestinationCidrBlock=''):
        rtb = self._route_tables_store.get(RouteTableId)
        if rtb is None:
            raise ClientError(
                {'Error': {'Code': 'InvalidRouteTableID.NotFound',
                            'Message': f'The route table id {RouteTableId} does not exist'}},
                'DeleteRoute')
        routes = rtb.get('Routes', []) or []
        kept   = [r for r in routes
                  if r.get('DestinationCidrBlock') != DestinationCidrBlock]
        if len(kept) == len(routes):
            raise ClientError(
                {'Error': {'Code': 'InvalidRoute.NotFound',
                            'Message': f'No route for {DestinationCidrBlock}'}},
                'DeleteRoute')
        rtb['Routes'] = kept
        return {}

    # ── mutations: Security Group ─────────────────────────────────────────────

    def create_security_group(self, GroupName='', Description='', VpcId='',
                              TagSpecifications=None, **_):
        sg_id    = self._next_id('sg')
        raw_tags = self._tags_from_specs(TagSpecifications, 'security-group')
        raw = {
            'GroupId'            : sg_id,
            'GroupName'          : GroupName,
            'VpcId'              : VpcId,
            'Description'        : Description,
            'OwnerId'            : '123456789012',
            'IpPermissions'      : [],
            'IpPermissionsEgress': [],
            'Tags'               : raw_tags,
        }
        self._security_groups_store[sg_id] = raw
        return {'GroupId': sg_id, 'Tags': raw_tags}

    def authorize_security_group_ingress(self, GroupId='', IpPermissions=None, **_):
        return self._authorize_sg_perm(GroupId, IpPermissions, key='IpPermissions',
                                        op='AuthorizeSecurityGroupIngress')

    def authorize_security_group_egress(self, GroupId='', IpPermissions=None, **_):
        return self._authorize_sg_perm(GroupId, IpPermissions, key='IpPermissionsEgress',
                                        op='AuthorizeSecurityGroupEgress')

    def revoke_security_group_ingress(self, GroupId='', IpPermissions=None, **_):
        return self._revoke_sg_perm(GroupId, IpPermissions, key='IpPermissions',
                                     op='RevokeSecurityGroupIngress')

    def revoke_security_group_egress(self, GroupId='', IpPermissions=None, **_):
        return self._revoke_sg_perm(GroupId, IpPermissions, key='IpPermissionsEgress',
                                     op='RevokeSecurityGroupEgress')

    def _authorize_sg_perm(self, sg_id: str, perms: list, key: str, op: str):
        sg = self._security_groups_store.get(sg_id)
        if sg is None:
            raise ClientError(
                {'Error': {'Code': 'InvalidGroup.NotFound',
                            'Message': f'The security group {sg_id} does not exist'}},
                op)
        existing = sg.get(key, []) or []
        for new in (perms or []):
            if self._perm_exists(existing, new):
                raise ClientError(
                    {'Error': {'Code': 'InvalidPermission.Duplicate',
                                'Message': 'rule already exists'}},
                    op)
            existing.append(new)
        sg[key] = existing
        return {}

    def _revoke_sg_perm(self, sg_id: str, perms: list, key: str, op: str):
        sg = self._security_groups_store.get(sg_id)
        if sg is None:
            raise ClientError(
                {'Error': {'Code': 'InvalidGroup.NotFound',
                            'Message': f'The security group {sg_id} does not exist'}},
                op)
        existing = sg.get(key, []) or []
        removed_any = False
        for new in (perms or []):
            for i, e in enumerate(list(existing)):
                if self._perm_matches(e, new):
                    existing.pop(i)
                    removed_any = True
                    break
        if not removed_any:
            raise ClientError(
                {'Error': {'Code': 'InvalidPermission.NotFound',
                            'Message': 'rule does not exist'}},
                op)
        sg[key] = existing
        return {}

    def _perm_exists(self, existing: list, new: dict) -> bool:
        for e in existing:
            if self._perm_matches(e, new):
                return True
        return False

    def _perm_matches(self, a: dict, b: dict) -> bool:
        if a.get('IpProtocol') != b.get('IpProtocol'): return False
        if a.get('FromPort')   != b.get('FromPort'):   return False
        if a.get('ToPort')     != b.get('ToPort'):     return False
        a_cidrs = sorted([r.get('CidrIp', '') for r in (a.get('IpRanges') or [])])
        b_cidrs = sorted([r.get('CidrIp', '') for r in (b.get('IpRanges') or [])])
        if a_cidrs != b_cidrs:
            return False
        a_sgs = sorted([r.get('GroupId', '') for r in (a.get('UserIdGroupPairs') or [])])
        b_sgs = sorted([r.get('GroupId', '') for r in (b.get('UserIdGroupPairs') or [])])
        if a_sgs != b_sgs:
            return False
        return True

    # ── internal ──────────────────────────────────────────────────────────────

    def _next_id(self, prefix: str) -> str:                                     # Deterministic counters per prefix; tests can assert on the produced IDs
        n = self._counters.get(prefix, 0) + 1
        self._counters[prefix] = n
        return f'{prefix}-{n:08x}'

    def _tags_from_specs(self, specs, resource_type: str) -> list:              # boto3 TagSpecifications → flat [{Key,Value},…]
        out = []
        for ts in (specs or []):
            if ts.get('ResourceType') != resource_type:
                continue
            for t in (ts.get('Tags') or []):
                out.append({'Key': t.get('Key', ''), 'Value': t.get('Value', '')})
        return out

    def _apply_tag_filters(self, resources: list, filters: list) -> list:      # Generic tag:K=V filter — used by vpc/subnet/igw/route-table
        result = resources
        for f in filters:
            name   = f.get('Name', '')
            values = f.get('Values', [])
            if not name.startswith('tag:'):
                continue
            key  = name[4:]
            kept = []
            for r in result:
                tags = {t.get('Key', ''): t.get('Value', '')
                        for t in (r.get('Tags', []) or [])}
                if key in tags and tags[key] in values:
                    kept.append(r)
            result = kept
        return result

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
        elif self._method == 'describe_vpcs':
            yield self._client.describe_vpcs(VpcIds=kwargs.get('VpcIds'),
                                              Filters=kwargs.get('Filters'))
        elif self._method == 'describe_subnets':
            yield self._client.describe_subnets(SubnetIds=kwargs.get('SubnetIds'),
                                                 Filters=kwargs.get('Filters'))
        elif self._method == 'describe_internet_gateways':
            yield self._client.describe_internet_gateways(
                InternetGatewayIds=kwargs.get('InternetGatewayIds'),
                Filters=kwargs.get('Filters'))
        elif self._method == 'describe_route_tables':
            yield self._client.describe_route_tables(
                RouteTableIds=kwargs.get('RouteTableIds'),
                Filters=kwargs.get('Filters'))


class EC2__AWS__Client__In_Memory(EC2__AWS__Client):

    def __init__(self):
        super().__init__()
        self._store                    = {}
        self._images_store             = {}
        self._snapshots_store          = {}
        self._security_groups_store    = {}
        self._network_interfaces_store = {}
        self._vpcs_store               = {}
        self._subnets_store            = {}
        self._internet_gateways_store  = {}
        self._route_tables_store       = {}
        self._counters                 = {}
        self._fake                     = _Fake_EC2_Client(
            self._store,
            images_store             = self._images_store,
            snapshots_store          = self._snapshots_store,
            security_groups_store    = self._security_groups_store,
            network_interfaces_store = self._network_interfaces_store,
            vpcs_store               = self._vpcs_store,
            subnets_store            = self._subnets_store,
            internet_gateways_store  = self._internet_gateways_store,
            route_tables_store       = self._route_tables_store,
            counters                 = self._counters,
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

    def seed_eni(self, eni_id: str = '', subnet_id: str = 'subnet-default',
                 vpc_id: str = 'vpc-default', public_ip: str = '',
                 private_ip: str = '10.0.0.1', sg_ids: list = None,
                 instance_id: str = '', attachment_status: str = 'attached',
                 status: str = 'in-use', description: str = '') -> str:
        if not eni_id:
            eni_id = f'eni-{secrets.token_hex(8)}'
        groups     = [{'GroupId': g, 'GroupName': g} for g in (sg_ids or [])]
        association = {'PublicIp': public_ip} if public_ip else {}
        attachment  = {}
        if instance_id:
            attachment = {'InstanceId': instance_id, 'Status': attachment_status}
        elif attachment_status:
            attachment = {'Status': attachment_status}
        raw = {
            'NetworkInterfaceId' : eni_id,
            'SubnetId'           : subnet_id,
            'VpcId'              : vpc_id,
            'Description'        : description,
            'Status'             : status,
            'Groups'             : groups,
            'Association'        : association,
            'Attachment'         : attachment,
            'PrivateIpAddresses' : [{'PrivateIpAddress': private_ip, 'Primary': True}],
        }
        self._network_interfaces_store[eni_id] = raw
        return eni_id

    # ── seed: VPCs ────────────────────────────────────────────────────────────

    def seed_vpc(self, vpc_id: str = '', cidr: str = '10.0.0.0/16',
                 is_default: bool = False, state: str = 'available',
                 dhcp_options_id: str = 'dopt-default',
                 instance_tenancy: str = 'default',
                 tags: dict = None) -> str:
        if not vpc_id:
            vpc_id = f'vpc-{secrets.token_hex(8)}'
        raw_tags = [{'Key': k, 'Value': v} for k, v in (tags or {}).items()]
        raw = {
            'VpcId'           : vpc_id,
            'CidrBlock'       : cidr,
            'IsDefault'       : is_default,
            'State'           : state,
            'DhcpOptionsId'   : dhcp_options_id,
            'InstanceTenancy' : instance_tenancy,
            'Tags'            : raw_tags,
        }
        self._vpcs_store[vpc_id] = raw
        return vpc_id

    # ── seed: Subnets ─────────────────────────────────────────────────────────

    def seed_subnet(self, subnet_id: str = '', vpc_id: str = 'vpc-default',
                    cidr: str = '10.0.1.0/24', az: str = 'eu-west-2a',
                    az_id: str = '', available_ip_count: int = 251,
                    public: bool = False, state: str = 'available',
                    tags: dict = None) -> str:
        if not subnet_id:
            subnet_id = f'subnet-{secrets.token_hex(8)}'
        raw_tags = [{'Key': k, 'Value': v} for k, v in (tags or {}).items()]
        raw = {
            'SubnetId'                : subnet_id,
            'VpcId'                   : vpc_id,
            'CidrBlock'               : cidr,
            'AvailabilityZone'        : az,
            'AvailabilityZoneId'      : az_id,
            'AvailableIpAddressCount' : available_ip_count,
            'MapPublicIpOnLaunch'     : public,
            'State'                   : state,
            'Tags'                    : raw_tags,
        }
        self._subnets_store[subnet_id] = raw
        return subnet_id

    # ── seed: Internet Gateways ───────────────────────────────────────────────

    def seed_igw(self, igw_id: str = '', vpc_id: str = '',
                 state: str = 'available', tags: dict = None) -> str:
        if not igw_id:
            igw_id = f'igw-{secrets.token_hex(8)}'
        raw_tags    = [{'Key': k, 'Value': v} for k, v in (tags or {}).items()]
        attachments = []
        if vpc_id:
            attachments.append({'VpcId': vpc_id, 'State': state or 'available'})
        raw = {
            'InternetGatewayId' : igw_id,
            'Attachments'       : attachments,
            'Tags'              : raw_tags,
        }
        self._internet_gateways_store[igw_id] = raw
        return igw_id

    # ── seed: Route Tables ────────────────────────────────────────────────────

    def seed_route_table(self, rtb_id: str = '', vpc_id: str = 'vpc-default',
                         routes: list = None, associations: list = None,
                         tags: dict = None) -> str:
        if not rtb_id:
            rtb_id = f'rtb-{secrets.token_hex(8)}'
        raw_tags    = [{'Key': k, 'Value': v} for k, v in (tags or {}).items()]
        # `routes` is a list of dicts (destination_cidr=…, gateway_id=…, …)
        # we map them into the boto3 shape the parser expects
        raw_routes = []
        for r in (routes or []):
            row = {
                'State'  : r.get('state',  'active'),
                'Origin' : r.get('origin', 'CreateRoute'),
            }
            dest = r.get('destination_cidr', '')
            if dest.startswith('pl-'):
                row['DestinationPrefixListId'] = dest
            elif ':' in dest:
                row['DestinationIpv6CidrBlock'] = dest
            else:
                row['DestinationCidrBlock'] = dest
            gw = r.get('gateway_id', '')
            if gw.startswith('igw-') or gw == 'local':
                row['GatewayId'] = gw
            elif gw.startswith('nat-'):
                row['NatGatewayId'] = gw
            elif gw.startswith('tgw-'):
                row['TransitGatewayId'] = gw
            elif gw.startswith('pcx-'):
                row['VpcPeeringConnectionId'] = gw
            elif gw:
                row['GatewayId'] = gw                                            # fallback so unknown prefixes still surface
            raw_routes.append(row)
        raw_assocs = []
        for a in (associations or []):
            raw_assocs.append({
                'RouteTableAssociationId' : a.get('association_id',
                                                  f'rtbassoc-{secrets.token_hex(8)}'),
                'RouteTableId'            : rtb_id,
                'SubnetId'                : a.get('subnet_id', ''),
                'Main'                    : bool(a.get('main', False)),
            })
        raw = {
            'RouteTableId' : rtb_id,
            'VpcId'        : vpc_id,
            'Routes'       : raw_routes,
            'Associations' : raw_assocs,
            'Tags'         : raw_tags,
        }
        self._route_tables_store[rtb_id] = raw
        return rtb_id
