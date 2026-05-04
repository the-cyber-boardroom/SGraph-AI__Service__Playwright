# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Prometheus__AMI__Helper
# AMI lookups for sp prom. Single responsibility: read-only AMI queries.
# AMI lifecycle (create / wait / tag / deregister) lives in a separate helper
# because that flow is only used by `sp prom ami` subcommands (per plan 5 P5).
# ═══════════════════════════════════════════════════════════════════════════════

import boto3                                                                        # EXCEPTION — narrow boto3 boundary, see plan doc 2

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.prometheus.service.Prometheus__AWS__Client   import TAG_PURPOSE_KEY, TAG_PURPOSE_VALUE


AL2023_NAME_FILTER = 'al2023-ami-2023.*-x86_64'
AMAZON_OWNER       = 'amazon'
TAG_AMI_STATUS_KEY = 'sg:ami-status'                                                # untested | healthy | unhealthy — same convention as sp el / sp os


class Prometheus__AMI__Helper(Type_Safe):

    def ec2_client(self, region: str):                                              # Single seam — tests override
        return boto3.client('ec2', region_name=region)

    def latest_al2023_ami_id(self, region: str) -> str:
        resp   = self.ec2_client(region).describe_images(
            Owners  = [AMAZON_OWNER]                                       ,
            Filters = [{'Name': 'name'        , 'Values': [AL2023_NAME_FILTER]},
                       {'Name': 'architecture', 'Values': ['x86_64']           },
                       {'Name': 'state'       , 'Values': ['available']        }])
        images = sorted(resp.get('Images', []), key=lambda x: x.get('CreationDate', ''), reverse=True)
        if not images:
            raise RuntimeError(f'No AL2023 AMI found in region {region!r}')
        return images[0].get('ImageId', '')

    def latest_healthy_ami_id(self, region: str) -> str:                            # Returns most recent sg:purpose=prometheus + sg:ami-status=healthy AMI; empty if none
        resp   = self.ec2_client(region).describe_images(
            Owners  = ['self']                                                                 ,
            Filters = [{'Name': f'tag:{TAG_PURPOSE_KEY}'   , 'Values': [TAG_PURPOSE_VALUE]   },
                       {'Name': f'tag:{TAG_AMI_STATUS_KEY}', 'Values': ['healthy']           },
                       {'Name': 'state'                    , 'Values': ['available']         }])
        images = sorted(resp.get('Images', []), key=lambda x: x.get('CreationDate', ''), reverse=True)
        return images[0].get('ImageId', '') if images else ''
