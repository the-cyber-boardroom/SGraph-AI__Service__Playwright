# ═══════════════════════════════════════════════════════════════════════════════
# Host Control Plane — Routes__Host__EC2
# GET /host/ec2-info → Schema__EC2__Info
# Uses the instance IMDS (169.254.169.254) to discover instance-id + region,
# then calls boto3 ec2.describe_instances() with the instance-profile creds.
# Security groups, volumes, tags, IAM profile, and network info are all included.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_fast_api.api.routes.Fast_API__Routes                                import Fast_API__Routes

from sg_compute.host_plane.host.schemas.Schema__EC2__Info                      import Schema__EC2__Info

TAG__ROUTES_HOST_EC2 = 'host'


def _imds(path: str, token: str) -> str:
    import urllib.request
    req = urllib.request.Request(
        f'http://169.254.169.254/latest/meta-data/{path}',
        headers={'X-aws-ec2-metadata-token': token},
    )
    with urllib.request.urlopen(req, timeout=2) as r:
        return r.read().decode().strip()


def _imds_token() -> str:
    import urllib.request
    req = urllib.request.Request(
        'http://169.254.169.254/latest/api/token',
        method='PUT',
        headers={'X-aws-ec2-metadata-token-ttl-seconds': '60'},
    )
    with urllib.request.urlopen(req, timeout=2) as r:
        return r.read().decode().strip()


class Routes__Host__EC2(Fast_API__Routes):
    tag : str = TAG__ROUTES_HOST_EC2

    def ec2_info(self) -> dict:                                             # GET /host/ec2-info
        info = Schema__EC2__Info()
        try:
            token       = _imds_token()
            instance_id = _imds('instance-id',        token)
            region      = _imds('placement/region',   token)
            az          = _imds('placement/availability-zone', token)
            info.instance_id       = instance_id
            info.region            = region
            info.availability_zone = az
        except Exception as ex:
            info.error = f'IMDS unavailable: {ex}'
            return info.json()

        try:
            import boto3
            ec2 = boto3.client('ec2', region_name=region)
            resp = ec2.describe_instances(InstanceIds=[instance_id])
            reservations = resp.get('Reservations', [])
            if not reservations:
                info.error = 'Instance not found in EC2 API'
                return info.json()
            instance = reservations[0]['Instances'][0]

            info.instance_type     = instance.get('InstanceType', '')
            info.ami_id            = instance.get('ImageId', '')
            info.launch_time       = str(instance.get('LaunchTime', ''))
            info.state             = instance.get('State', {}).get('Name', '')
            info.public_ip         = instance.get('PublicIpAddress', '')
            info.private_ip        = instance.get('PrivateIpAddress', '')
            info.public_dns        = instance.get('PublicDnsName', '')
            info.private_dns       = instance.get('PrivateDnsName', '')
            info.vpc_id            = instance.get('VpcId', '')
            info.subnet_id         = instance.get('SubnetId', '')

            profile = instance.get('IamInstanceProfile', {})
            info.iam_profile_arn   = profile.get('Arn', '')
            info.iam_profile_name  = info.iam_profile_arn.split('/')[-1] if info.iam_profile_arn else ''

            info.tags = {t['Key']: t['Value'] for t in instance.get('Tags', [])}

            # volumes
            vols = []
            for mapping in instance.get('BlockDeviceMappings', []):
                vols.append({
                    'device'   : mapping.get('DeviceName', ''),
                    'volume_id': mapping.get('Ebs', {}).get('VolumeId', ''),
                    'status'   : mapping.get('Ebs', {}).get('Status', ''),
                })
            # enrich volumes with size from describe_volumes
            if vols:
                vol_ids = [v['volume_id'] for v in vols if v['volume_id']]
                if vol_ids:
                    try:
                        vresp = ec2.describe_volumes(VolumeIds=vol_ids)
                        size_map = {v['VolumeId']: v for v in vresp.get('Volumes', [])}
                        for v in vols:
                            detail = size_map.get(v['volume_id'], {})
                            v['size_gb']   = detail.get('Size', 0)
                            v['volume_type'] = detail.get('VolumeType', '')
                            v['encrypted'] = detail.get('Encrypted', False)
                    except Exception:
                        pass
            info.volumes = vols

            # security groups — include inbound/outbound rules
            sg_ids = [sg['GroupId'] for sg in instance.get('SecurityGroups', [])]
            if sg_ids:
                sgresp = ec2.describe_security_groups(GroupIds=sg_ids)
                sgs = []
                for sg in sgresp.get('SecurityGroups', []):
                    def _fmt_rules(rules):
                        out = []
                        for r in rules:
                            proto = r.get('IpProtocol', '')
                            port_range = ''
                            if proto not in ('-1', 'icmp'):
                                lo = r.get('FromPort', '')
                                hi = r.get('ToPort', '')
                                port_range = f'{lo}' if lo == hi else f'{lo}-{hi}'
                            cidrs = [ip['CidrIp'] for ip in r.get('IpRanges', [])]
                            cidrs += [ip['CidrIpv6'] for ip in r.get('Ipv6Ranges', [])]
                            out.append({
                                'protocol'  : 'all' if proto == '-1' else proto,
                                'ports'     : port_range or 'all',
                                'sources'   : cidrs or ['(sg-ref)'],
                                'description': r.get('Description', ''),
                            })
                        return out
                    sgs.append({
                        'id'      : sg.get('GroupId', ''),
                        'name'    : sg.get('GroupName', ''),
                        'desc'    : sg.get('Description', ''),
                        'inbound' : _fmt_rules(sg.get('IpPermissions',       [])),
                        'outbound': _fmt_rules(sg.get('IpPermissionsEgress', [])),
                    })
                info.security_groups = sgs

        except Exception as ex:
            info.error = f'EC2 API error: {ex}'

        return info.json()
    ec2_info.__route_path__ = '/ec2-info'

    def setup_routes(self):
        self.add_route_get(self.ec2_info)
