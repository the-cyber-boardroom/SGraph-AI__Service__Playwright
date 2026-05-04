# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Routes__Stack__Catalog
# Read-only endpoints: type catalog, plugin manifest, cross-section stack list,
# and EC2 instance detail (security groups, volumes, IAM, network, tags).
# EC2 info uses the SP CLI IAM credentials — NOT the sidecar (no IAM on nodes).
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi                                                                         import Query
from osbot_fast_api.api.routes.Fast_API__Routes                                     import Fast_API__Routes

from sgraph_ai_service_playwright__cli.catalog.service.Stack__Catalog__Service      import Stack__Catalog__Service


class Routes__Stack__Catalog(Fast_API__Routes):
    tag     : str                  = 'catalog'
    service : Stack__Catalog__Service

    def types(self) -> dict:
        return self.service.get_catalog().json()
    types.__route_path__ = '/types'

    def manifest(self) -> dict:
        return self.service.get_manifest().json()
    manifest.__route_path__ = '/manifest'

    def stacks(self) -> dict:
        return self.service.list_all_stacks().json()
    stacks.__route_path__ = '/stacks'

    def setup_routes(self):
        self.add_route_get(self.types   )
        self.add_route_get(self.manifest)
        self.add_route_get(self.stacks  )
        router = self.router

        @router.get('/ec2-info')
        def ec2_info(instance_id: str = Query(...), region: str = Query(...)) -> dict:
            return _fetch_ec2_info(instance_id, region)


def _fetch_ec2_info(instance_id: str, region: str) -> dict:
    out = {'instance_id': instance_id, 'region': region,
           'instance_type': '', 'ami_id': '', 'launch_time': '', 'state': '',
           'availability_zone': '', 'public_ip': '', 'private_ip': '',
           'public_dns': '', 'private_dns': '', 'vpc_id': '', 'subnet_id': '',
           'iam_profile_arn': '', 'iam_profile_name': '',
           'security_groups': [], 'volumes': [], 'tags': {}, 'error': ''}
    try:
        import boto3                                                                 # EXCEPTION — narrow boto3 boundary
        ec2  = boto3.client('ec2', region_name=region)
        resp = ec2.describe_instances(InstanceIds=[instance_id])
        reservations = resp.get('Reservations', [])
        if not reservations:
            out['error'] = 'Instance not found'
            return out
        inst = reservations[0]['Instances'][0]

        out['instance_type']     = inst.get('InstanceType', '')
        out['ami_id']            = inst.get('ImageId', '')
        out['launch_time']       = str(inst.get('LaunchTime', ''))
        out['state']             = inst.get('State', {}).get('Name', '')
        out['availability_zone'] = inst.get('Placement', {}).get('AvailabilityZone', '')
        out['public_ip']         = inst.get('PublicIpAddress', '')
        out['private_ip']        = inst.get('PrivateIpAddress', '')
        out['public_dns']        = inst.get('PublicDnsName', '')
        out['private_dns']       = inst.get('PrivateDnsName', '')
        out['vpc_id']            = inst.get('VpcId', '')
        out['subnet_id']         = inst.get('SubnetId', '')
        profile                  = inst.get('IamInstanceProfile', {})
        out['iam_profile_arn']   = profile.get('Arn', '')
        out['iam_profile_name']  = out['iam_profile_arn'].split('/')[-1]
        out['tags']              = {t['Key']: t['Value'] for t in inst.get('Tags', [])}

        vols = []
        for m in inst.get('BlockDeviceMappings', []):
            vols.append({'device': m.get('DeviceName', ''),
                         'volume_id': m.get('Ebs', {}).get('VolumeId', ''),
                         'status': m.get('Ebs', {}).get('Status', '')})
        vol_ids = [v['volume_id'] for v in vols if v['volume_id']]
        if vol_ids:
            try:
                vresp = ec2.describe_volumes(VolumeIds=vol_ids)
                size_map = {v['VolumeId']: v for v in vresp.get('Volumes', [])}
                for v in vols:
                    d = size_map.get(v['volume_id'], {})
                    v['size_gb'] = d.get('Size', 0); v['volume_type'] = d.get('VolumeType', '')
                    v['encrypted'] = d.get('Encrypted', False)
            except Exception:
                pass
        out['volumes'] = vols

        sg_ids = [sg['GroupId'] for sg in inst.get('SecurityGroups', [])]
        if sg_ids:
            def _fmt(rules):
                result = []
                for r in rules:
                    proto = r.get('IpProtocol', '')
                    lo, hi = r.get('FromPort', ''), r.get('ToPort', '')
                    ports = 'all' if proto == '-1' else (str(lo) if lo == hi else f'{lo}-{hi}')
                    cidrs = [ip['CidrIp'] for ip in r.get('IpRanges', [])]
                    cidrs += [ip['CidrIpv6'] for ip in r.get('Ipv6Ranges', [])]
                    result.append({'protocol': 'all' if proto == '-1' else proto,
                                   'ports': ports, 'sources': cidrs or ['(sg-ref)'],
                                   'description': r.get('Description', '')})
                return result
            sgresp = ec2.describe_security_groups(GroupIds=sg_ids)
            out['security_groups'] = [
                {'id': sg['GroupId'], 'name': sg['GroupName'], 'desc': sg.get('Description', ''),
                 'inbound': _fmt(sg.get('IpPermissions', [])),
                 'outbound': _fmt(sg.get('IpPermissionsEgress', []))}
                for sg in sgresp.get('SecurityGroups', [])
            ]
    except Exception as ex:
        out['error'] = str(ex)
    return out
