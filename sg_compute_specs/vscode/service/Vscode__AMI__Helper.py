# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vscode: Vscode__AMI__Helper
# Resolves the base AMI for the vscode stack — plain Amazon Linux 2023 (x86_64).
# code-server runs in Docker, so no GPU/DLAMI is needed.
# ═══════════════════════════════════════════════════════════════════════════════

import boto3                                                                   # EXCEPTION — narrow boto3 boundary

from osbot_utils.type_safe.Type_Safe import Type_Safe


AL2023_SSM_PARAM = '/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64'


class Vscode__AMI__Helper(Type_Safe):

    def ssm_client(self, region: str):
        return boto3.client('ssm', region_name=region)

    def latest_al2023(self, region: str) -> str:
        resp = self.ssm_client(region).get_parameter(Name=AL2023_SSM_PARAM)
        return resp.get('Parameter', {}).get('Value', '')

    def resolve(self, region: str) -> str:
        return self.latest_al2023(region)
