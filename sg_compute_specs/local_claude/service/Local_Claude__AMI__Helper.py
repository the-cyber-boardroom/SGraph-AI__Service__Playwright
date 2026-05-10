# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — local-claude: Local_Claude__AMI__Helper
# Resolves the base AMI for the local-claude stack.
#
# DLAMI (default): Deep Learning OSS Nvidia Driver AMI for AL2023 — ships with
# the NVIDIA kernel driver that the Container Toolkit requires. Resolved by
# searching for the most recent `Deep Learning OSS Nvidia Driver AMI GPU *
# (Amazon Linux 2023)*` image owned by Amazon.
#
# AL2023 (plain): no NVIDIA drivers. Only useful when launching a CPU-only
# instance or when a custom AMI with drivers baked in is supplied via --ami.
# ═══════════════════════════════════════════════════════════════════════════════

import boto3                                                                   # EXCEPTION — narrow boto3 boundary

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute_specs.local_claude.enums.Enum__Local_Claude__AMI__Base import Enum__Local_Claude__AMI__Base


AL2023_SSM_PARAM = '/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64'
DLAMI_NAME_FILTER = 'Deep Learning OSS Nvidia Driver AMI GPU * (Amazon Linux 2023)*'


class Local_Claude__AMI__Helper(Type_Safe):

    def ssm_client(self, region: str):
        return boto3.client('ssm', region_name=region)

    def ec2_client(self, region: str):
        return boto3.client('ec2', region_name=region)

    def latest_al2023(self, region: str) -> str:
        return self._read_ssm_param(region, AL2023_SSM_PARAM)

    def latest_dlami(self, region: str) -> str:
        resp   = self.ec2_client(region).describe_images(
            Owners  = ['amazon'],
            Filters = [
                {'Name': 'name',  'Values': [DLAMI_NAME_FILTER]},
                {'Name': 'state', 'Values': ['available']},
            ],
        )
        images = sorted(resp.get('Images', []),
                        key=lambda i: i.get('CreationDate', ''), reverse=True)
        if not images:
            raise ValueError(
                f'No DLAMI matching {DLAMI_NAME_FILTER!r} found in {region}. '
                'Pass --ami <ami-id> to specify a GPU AMI manually.')
        return images[0]['ImageId']

    def resolve_for_base(self, region: str, base: Enum__Local_Claude__AMI__Base) -> str:
        if base == Enum__Local_Claude__AMI__Base.DLAMI:
            return self.latest_dlami(region)
        if base == Enum__Local_Claude__AMI__Base.AL2023:
            return self.latest_al2023(region)
        raise ValueError(f'unknown AMI base: {base}')

    def _read_ssm_param(self, region: str, param_name: str) -> str:
        resp = self.ssm_client(region).get_parameter(Name=param_name)
        return resp.get('Parameter', {}).get('Value', '')
