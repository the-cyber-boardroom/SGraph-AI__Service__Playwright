# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Docker: tests for Docker__Launch__Helper
# Pure kwargs builder — no AWS calls.
# ═══════════════════════════════════════════════════════════════════════════════

import base64
from unittest                                                                      import TestCase

from sg_compute_specs.docker.service.Docker__Launch__Helper                       import (AL2023_ROOT_DEVICE_NAME ,
                                                                                            Docker__Launch__Helper )


class test_Docker__Launch__Helper(TestCase):

    def setUp(self):
        self.helper = Docker__Launch__Helper()
        self.tags   = [{'Key': 'Name', 'Value': 'docker-fast-fermi'}]

    def _build(self, **overrides):
        defaults = dict(ami_id            = 'ami-0000000000000000a' ,
                        security_group_id = 'sg-1234'               ,
                        user_data         = 'echo hello'            ,
                        tags              = self.tags               )
        defaults.update(overrides)
        return self.helper.build_run_instances_kwargs(**defaults)

    def test_build__defaults_have_no_block_device_mapping(self):
        kwargs = self._build()
        assert 'BlockDeviceMappings' not in kwargs                                  # 0 = use AMI default
        assert kwargs['InstanceType']           == 't3.medium'
        assert kwargs['SecurityGroupIds']       == ['sg-1234']
        assert kwargs['MinCount']               == 1
        assert kwargs['MaxCount']               == 1
        assert kwargs['TagSpecifications']      == [{'ResourceType': 'instance', 'Tags': self.tags}]
        assert base64.b64decode(kwargs['UserData']).decode() == 'echo hello'

    def test_build__zero_disk_size_keeps_ami_default(self):
        kwargs = self._build(disk_size_gb=0)
        assert 'BlockDeviceMappings' not in kwargs

    def test_build__positive_disk_size_sets_root_volume(self):
        kwargs = self._build(disk_size_gb=200)
        assert kwargs['BlockDeviceMappings'] == [{
            'DeviceName' : AL2023_ROOT_DEVICE_NAME,
            'Ebs'        : {'VolumeSize'         : 200  ,
                            'VolumeType'         : 'gp3',
                            'DeleteOnTermination': True }
        }]

    def test_build__instance_profile_set_when_provided(self):
        kwargs = self._build(instance_profile_name='playwright-ec2')
        assert kwargs['IamInstanceProfile'] == {'Name': 'playwright-ec2'}

    def test_build__instance_profile_absent_when_blank(self):
        kwargs = self._build()
        assert 'IamInstanceProfile' not in kwargs

    def test_build__large_disk_passes_through(self):
        kwargs = self._build(disk_size_gb=1000)
        assert kwargs['BlockDeviceMappings'][0]['Ebs']['VolumeSize'] == 1000
