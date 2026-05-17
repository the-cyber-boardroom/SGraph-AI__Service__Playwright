# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Prometheus: Prometheus__AMI__Helper
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute_specs.prometheus.service.Prometheus__Tags                    import TAG_PURPOSE_KEY, TAG_PURPOSE_VALUE


AL2023_NAME_FILTER = 'al2023-ami-2023.*-x86_64'
AMAZON_OWNER       = 'amazon'
TAG_AMI_STATUS_KEY = 'sg:ami-status'


class Prometheus__AMI__Helper(Type_Safe):

    def ec2_client(self, region: str):
        from sgraph_ai_service_playwright__cli.credentials.service.Sg__Aws__Session  import Sg__Aws__Session
        from sgraph_ai_service_playwright__cli.credentials.service.Credentials__Store import Credentials__Store
        return Sg__Aws__Session(store=Credentials__Store()).boto3_client_from_context(
            service_name='ec2', region=region or '')

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

    def latest_healthy_ami_id(self, region: str) -> str:
        resp   = self.ec2_client(region).describe_images(
            Owners  = ['self']                                                                ,
            Filters = [{'Name': f'tag:{TAG_PURPOSE_KEY}'   , 'Values': [TAG_PURPOSE_VALUE]  },
                       {'Name': f'tag:{TAG_AMI_STATUS_KEY}', 'Values': ['healthy']          },
                       {'Name': 'state'                    , 'Values': ['available']        }])
        images = sorted(resp.get('Images', []), key=lambda x: x.get('CreationDate', ''), reverse=True)
        return images[0].get('ImageId', '') if images else ''
