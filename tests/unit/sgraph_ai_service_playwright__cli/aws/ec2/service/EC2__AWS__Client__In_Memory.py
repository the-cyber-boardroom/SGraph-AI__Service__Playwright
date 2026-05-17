# ═══════════════════════════════════════════════════════════════════════════════
# Tests — EC2__AWS__Client__In_Memory
# Dict-backed fake boto3 EC2 client for unit tests. No mocks. No patches.
# Supports describe_instances, run_instances, start/stop/terminate, tags.
# ═══════════════════════════════════════════════════════════════════════════════

import secrets
from datetime import datetime, timezone

from sgraph_ai_service_playwright__cli.aws.ec2.service.EC2__AWS__Client import EC2__AWS__Client


class _Fake_EC2_Client:                                                        # Minimal boto3-alike EC2 client backed by in-memory dicts

    def __init__(self, store: dict):
        self._store = store                                                     # instance_id → raw instance dict

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


class EC2__AWS__Client__In_Memory(EC2__AWS__Client):

    def __init__(self):
        super().__init__()
        self._store = {}
        self._fake  = _Fake_EC2_Client(self._store)

    def client(self):
        return self._fake

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
