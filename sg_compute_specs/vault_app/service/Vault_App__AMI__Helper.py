# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-app: Vault_App__AMI__Helper
# Resolves the base AMI for a vault-app stack.
#
# Default: latest Amazon Linux 2023 (x86_64), resolved from the SSM public
# parameter store. vault-app is CPU-only — no GPU / DLAMI variants.
#
# Fast-boot path: bake an AMI from a warm stack (`sg vault-app ami bake`) with
# the container images already pulled, then launch with `--ami <id>`. Boot then
# skips the dnf install + ECR pull entirely. `from_ami` overrides this helper.
# ═══════════════════════════════════════════════════════════════════════════════

import boto3                                                                   # EXCEPTION — narrow boto3 boundary

from osbot_utils.type_safe.Type_Safe import Type_Safe


AL2023_SSM_PARAM = '/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64'


class Vault_App__AMI__Helper(Type_Safe):

    def ssm_client(self, region: str):
        return boto3.client('ssm', region_name=region)

    def latest_al2023(self, region: str) -> str:
        resp = self.ssm_client(region).get_parameter(Name=AL2023_SSM_PARAM)
        return resp.get('Parameter', {}).get('Value', '')

    def resolve(self, region: str, from_ami: str = '') -> str:
        return from_ami or self.latest_al2023(region)
