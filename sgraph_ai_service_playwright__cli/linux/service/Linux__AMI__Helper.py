# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Linux__AMI__Helper
# Resolves the latest AL2023 AMI for a given region. Uses the SSM public
# parameter path which always points to the latest AMI — avoids hardcoding
# AMI IDs per-region.
# ═══════════════════════════════════════════════════════════════════════════════

import boto3                                                                        # EXCEPTION — narrow boto3 boundary, see plan doc

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe


AL2023_SSM_PARAM = '/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64'


class Linux__AMI__Helper(Type_Safe):

    def ssm_client(self, region: str):
        return boto3.client('ssm', region_name=region)

    def latest_al2023_ami_id(self, region: str) -> str:                             # Resolved via SSM public parameter — always up-to-date
        resp = self.ssm_client(region).get_parameter(Name=AL2023_SSM_PARAM)
        return resp.get('Parameter', {}).get('Value', '')
