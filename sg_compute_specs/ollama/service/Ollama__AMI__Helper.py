# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Ollama: Ollama__AMI__Helper
# Resolves the AMI ID to launch from based on Enum__Ollama__AMI__Base.
# DLAMI default: x86_64 OSS NVIDIA driver GPU PyTorch 2.6 on Amazon Linux 2023.
# ═══════════════════════════════════════════════════════════════════════════════

from typing import Optional

import boto3                                                                  # EXCEPTION — narrow boto3 boundary

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute_specs.ollama.enums.Enum__Ollama__AMI__Base import Enum__Ollama__AMI__Base


DLAMI_OSS_PYTORCH_26_SSM_PARAM = ('/aws/service/deeplearning/ami/x86_64/'
                                   'oss-nvidia-driver-gpu-pytorch-2.6-amazon-linux-2023/'
                                   'latest/ami-id')
AL2023_SSM_PARAM = '/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64'


class Ollama__AMI__Helper(Type_Safe):

    def ssm_client(self, region: str):
        return boto3.client('ssm', region_name=region)

    def latest_dlami_oss_pytorch_26(self, region: str) -> str:
        return self._read_ssm_param(region, DLAMI_OSS_PYTORCH_26_SSM_PARAM)

    def latest_al2023(self, region: str) -> str:
        return self._read_ssm_param(region, AL2023_SSM_PARAM)

    def resolve_for_base(self, region: str, base: Enum__Ollama__AMI__Base) -> str:
        if base == Enum__Ollama__AMI__Base.DLAMI:
            return self.latest_dlami_oss_pytorch_26(region)
        if base == Enum__Ollama__AMI__Base.AL2023:
            return self.latest_al2023(region)
        raise ValueError(f'unknown AMI base: {base}')

    def _read_ssm_param(self, region: str, param_name: str) -> str:
        resp = self.ssm_client(region).get_parameter(Name=param_name)
        return resp.get('Parameter', {}).get('Value', '')
