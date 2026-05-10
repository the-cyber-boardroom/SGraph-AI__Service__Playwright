# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — local-claude: Local_Claude__AMI__Helper
# Resolves the base AMI for the local-claude stack. Only AL2023 in v1 — NVIDIA
# drivers are provided by the container toolkit, not a host-level DLAMI.
# ═══════════════════════════════════════════════════════════════════════════════

import boto3                                                                  # EXCEPTION — narrow boto3 boundary

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute_specs.local_claude.enums.Enum__Local_Claude__AMI__Base import Enum__Local_Claude__AMI__Base


AL2023_SSM_PARAM = '/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64'


class Local_Claude__AMI__Helper(Type_Safe):

    def ssm_client(self, region: str):
        return boto3.client('ssm', region_name=region)

    def latest_al2023(self, region: str) -> str:
        return self._read_ssm_param(region, AL2023_SSM_PARAM)

    def resolve_for_base(self, region: str, base: Enum__Local_Claude__AMI__Base) -> str:
        if base == Enum__Local_Claude__AMI__Base.AL2023:
            return self.latest_al2023(region)
        raise ValueError(f'unknown AMI base: {base}')

    def _read_ssm_param(self, region: str, param_name: str) -> str:
        resp = self.ssm_client(region).get_parameter(Name=param_name)
        return resp.get('Parameter', {}).get('Value', '')
