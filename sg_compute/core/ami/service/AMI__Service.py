# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — AMI__Service
# Bake/delete/describe-state operations for spec-tagged AMIs.
# Extends AMI__Lister so list_amis() comes free; tag conventions shared.
# All AMIs created here carry sg-compute-spec / sg-source-stack /
# sg-source-instance tags so AMI__Lister can find them later.
# ═══════════════════════════════════════════════════════════════════════════════

import boto3                                                                   # EXCEPTION — narrow boto3 boundary for EC2 AMI ops

from sg_compute.core.ami.schemas.Schema__AMI__Info import Schema__AMI__Info
from sg_compute.core.ami.service.AMI__Lister      import (AMI__Lister             ,
                                                           TAG_KEY__SOURCE_INSTANCE,
                                                           TAG_KEY__SOURCE_STACK   ,
                                                           TAG_KEY__SPEC           )


class AMI__Service(AMI__Lister):

    def bake(self, region       : str ,
                   spec_id      : str ,
                   instance_id  : str ,
                   ami_name     : str ,
                   source_stack : str  = '' ,
                   no_reboot    : bool = True) -> Schema__AMI__Info:                # Returns Schema__AMI__Info; AWS marks the image 'pending' initially
        ec2  = boto3.client('ec2', region_name=region)
        tags = [{'Key': TAG_KEY__SPEC           , 'Value': spec_id     },
                {'Key': TAG_KEY__SOURCE_INSTANCE, 'Value': instance_id },
                {'Key': TAG_KEY__SOURCE_STACK   , 'Value': source_stack},
                {'Key': 'Name'                  , 'Value': ami_name    }]
        resp   = ec2.create_image(
            InstanceId        = instance_id,
            Name              = ami_name   ,
            Description       = f'sp {spec_id} ami bake from {source_stack or instance_id}',
            NoReboot          = no_reboot  ,
            TagSpecifications = [{'ResourceType': 'image'   , 'Tags': tags},
                                 {'ResourceType': 'snapshot', 'Tags': tags}],
        )
        return Schema__AMI__Info(ami_id          = str(resp.get('ImageId', '')),
                                 name            = ami_name                    ,
                                 state           = 'pending'                   ,
                                 source_stack    = source_stack                ,
                                 source_instance = instance_id                 )

    def delete(self, region: str, ami_id: str) -> tuple:                            # Returns (deregistered: bool, snapshots_deleted: int)
        ec2 = boto3.client('ec2', region_name=region)
        try:
            describe = ec2.describe_images(ImageIds=[ami_id])
        except Exception:
            return False, 0
        images = describe.get('Images', [])
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
        for snap_id in snapshot_ids:                                                # Snapshots survive deregister_image; explicit delete needed to free the storage
            try:
                ec2.delete_snapshot(SnapshotId=snap_id)
                deleted += 1
            except Exception:
                pass
        return True, deleted

    def describe_state(self, region: str, ami_id: str) -> str:                      # 'pending' / 'available' / 'failed' / ''
        try:
            resp   = boto3.client('ec2', region_name=region).describe_images(ImageIds=[ami_id])
            images = resp.get('Images', [])
            return str(images[0].get('State', '')) if images else ''
        except Exception:
            return ''
