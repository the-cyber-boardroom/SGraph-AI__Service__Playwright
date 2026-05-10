# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — AMI__Lister
# Lists spec-tagged AMIs owned by this account via EC2 describe_images.
# Filter: tag sg-compute-spec=<spec_id>, state=available, owner=self.
# Ordered newest-first by CreationDate.
# ═══════════════════════════════════════════════════════════════════════════════

import boto3                                                                   # EXCEPTION — narrow boto3 boundary for EC2 AMI queries

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute.core.ami.schemas.Schema__AMI__Info          import Schema__AMI__Info
from sg_compute.core.ami.schemas.Schema__AMI__List__Response import Schema__AMI__List__Response

TAG_KEY__SPEC            = 'sg-compute-spec'
TAG_KEY__SOURCE_STACK    = 'sg-source-stack'
TAG_KEY__SOURCE_INSTANCE = 'sg-source-instance'


class AMI__Lister(Type_Safe):
    region : str = 'eu-west-2'

    def _ec2_client(self):
        return boto3.client('ec2', region_name=self.region)

    def list_amis(self, spec_id: str) -> Schema__AMI__List__Response:
        try:
            raw = self._ec2_client().describe_images(
                Owners  = ['self'],
                Filters = [
                    {'Name': f'tag:{TAG_KEY__SPEC}', 'Values': [spec_id]},
                    {'Name': 'state'               , 'Values': ['available']},
                ],
            )
        except Exception:
            return Schema__AMI__List__Response(spec_id=spec_id)

        images = sorted(raw.get('Images', []),
                        key=lambda i: i.get('CreationDate', ''),
                        reverse=True)

        amis = [self._map_image(img) for img in images]
        resp = Schema__AMI__List__Response(spec_id=spec_id)
        for ami in amis:
            resp.amis.append(ami)
        return resp

    @staticmethod
    def _map_image(raw: dict) -> Schema__AMI__Info:
        block_mappings = raw.get('BlockDeviceMappings', [])
        size_gb        = 0
        for mapping in block_mappings:
            ebs = mapping.get('Ebs', {})
            if ebs.get('VolumeSize'):
                size_gb = ebs['VolumeSize']
                break
        tags = {t.get('Key', ''): t.get('Value', '') for t in (raw.get('Tags') or [])}
        return Schema__AMI__Info(ami_id          = raw.get('ImageId'     , ''),
                                 name            = raw.get('Name'        , ''),
                                 created_at      = raw.get('CreationDate', ''),
                                 state           = raw.get('State'       , ''),
                                 size_gb         = size_gb                    ,
                                 source_stack    = tags.get(TAG_KEY__SOURCE_STACK   , ''),
                                 source_instance = tags.get(TAG_KEY__SOURCE_INSTANCE, ''))
