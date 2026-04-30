# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Firefox__AMI__Helper
# AMI operations for sp firefox: lookup latest AL2023, bake, list, delete.
# ═══════════════════════════════════════════════════════════════════════════════

import boto3                                                                        # EXCEPTION — narrow boto3 boundary

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.firefox.service.Firefox__AWS__Client         import TAG_PURPOSE_KEY, TAG_PURPOSE_VALUE, TAG_STACK_NAME_KEY


AL2023_NAME_FILTER = 'al2023-ami-2023.*-x86_64'
AMAZON_OWNER       = 'amazon'


class Firefox__AMI__Helper(Type_Safe):

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

    def create_image(self, region: str, instance_id: str, stack_name: str,
                     ami_name: str, no_reboot: bool = True) -> str:                 # Returns ami-id; AWS marks it pending initially
        ec2  = self.ec2_client(region)
        tags = [{'Key': TAG_PURPOSE_KEY       , 'Value': TAG_PURPOSE_VALUE         },
                {'Key': TAG_STACK_NAME_KEY     , 'Value': str(stack_name)           },
                {'Key': 'sg:source-instance'   , 'Value': instance_id              },
                {'Key': 'Name'                 , 'Value': ami_name                  }]
        resp = ec2.create_image(
            InstanceId        = instance_id ,
            Name              = ami_name    ,
            Description       = f'sp firefox ami create from {stack_name}',
            NoReboot          = no_reboot   ,
            TagSpecifications = [{'ResourceType': 'image'   , 'Tags': tags},
                                  {'ResourceType': 'snapshot', 'Tags': tags}])
        return str(resp.get('ImageId', ''))

    def list_firefox_amis(self, region: str) -> list:
        ec2 = self.ec2_client(region)
        try:
            resp = ec2.describe_images(
                Owners  = ['self'],
                Filters = [{'Name': f'tag:{TAG_PURPOSE_KEY}', 'Values': [TAG_PURPOSE_VALUE]}])
        except Exception:
            return []
        amis = []
        for img in resp.get('Images', []) or []:
            tags = {t.get('Key'): t.get('Value') for t in (img.get('Tags') or [])}
            amis.append({
                'ami_id'       : str(img.get('ImageId'     , '')),
                'name'         : str(img.get('Name'        , '')),
                'creation_date': str(img.get('CreationDate', '')),
                'state'        : str(img.get('State'       , '')),
                'source_stack' : str(tags.get(TAG_STACK_NAME_KEY    , '')),
                'source_id'    : str(tags.get('sg:source-instance'  , '')),
                'snapshot_ids' : [bdm.get('Ebs', {}).get('SnapshotId', '')
                                   for bdm in img.get('BlockDeviceMappings', []) or []
                                   if bdm.get('Ebs', {}).get('SnapshotId')],
            })
        return amis

    def describe_ami_state(self, region: str, ami_id: str) -> str:                  # 'pending' / 'available' / 'failed' / ''
        try:
            resp   = self.ec2_client(region).describe_images(ImageIds=[ami_id])
            images = resp.get('Images', [])
            return str(images[0].get('State', '')) if images else ''
        except Exception:
            return ''

    def deregister_ami(self, region: str, ami_id: str) -> tuple:                    # (deregistered: bool, deleted_snapshots: int)
        ec2 = self.ec2_client(region)
        try:
            describe     = ec2.describe_images(ImageIds=[ami_id])
            images       = describe.get('Images', [])
        except Exception:
            return False, 0
        if not images:
            return False, 0
        snapshot_ids = [bdm.get('Ebs', {}).get('SnapshotId', '')
                         for bdm in images[0].get('BlockDeviceMappings', []) or []
                         if bdm.get('Ebs', {}).get('SnapshotId')]
        try:
            ec2.deregister_image(ImageId=ami_id)
        except Exception:
            return False, 0
        deleted = 0
        for snap_id in snapshot_ids:
            try:
                ec2.delete_snapshot(SnapshotId=snap_id)
                deleted += 1
            except Exception:
                pass
        return True, deleted
