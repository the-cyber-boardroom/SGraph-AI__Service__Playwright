# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Neko__AMI__Helper
# AMI lookups for sp neko. Mirrors VNC / Prometheus helpers.
# ═══════════════════════════════════════════════════════════════════════════════

import boto3                                                                        # EXCEPTION — narrow boto3 boundary

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe


AL2023_NAME_FILTER = 'al2023-ami-2023.*-x86_64'
AMAZON_OWNER       = 'amazon'


class Neko__AMI__Helper(Type_Safe):

    def ec2_client(self, region: str):
        return boto3.client('ec2', region_name=region)

    def latest_al2023_ami_id(self, region: str) -> str:
        resp   = self.ec2_client(region).describe_images(
            Owners  = [AMAZON_OWNER],
            Filters = [{'Name': 'name'        , 'Values': [AL2023_NAME_FILTER]},
                       {'Name': 'architecture', 'Values': ['x86_64']          },
                       {'Name': 'state'       , 'Values': ['available']       }])
        images = sorted(resp.get('Images', []), key=lambda x: x.get('CreationDate', ''), reverse=True)
        if not images:
            raise RuntimeError(f'No AL2023 AMI found in region {region!r}')
        return images[0].get('ImageId', '')
