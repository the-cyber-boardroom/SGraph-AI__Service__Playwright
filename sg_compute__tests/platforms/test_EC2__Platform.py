# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute tests — EC2__Platform
# Tests that don't require AWS credentials.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                 import TestCase

from sg_compute.platforms.Platform                                           import Platform
from sg_compute.platforms.ec2.EC2__Platform                                 import EC2__Platform
from sg_compute.primitives.enums.Enum__Node__State                          import Enum__Node__State


class test_EC2__Platform(TestCase):

    def test_is_platform_subclass(self):
        assert issubclass(EC2__Platform, Platform)

    def test_name(self):
        p = EC2__Platform()
        assert p.name == 'ec2'

    def test_setup_returns_self(self):
        p = EC2__Platform()
        assert p.setup() is p

    def test_raw_to_node_info_running(self):
        p   = EC2__Platform()
        raw = {
            'InstanceId'       : 'i-0abc123'           ,
            'InstanceType'     : 't3.large'             ,
            'ImageId'          : 'ami-0xyz'             ,
            'PublicIpAddress'  : '1.2.3.4'              ,
            'PrivateIpAddress' : '10.0.0.1'             ,
            'State'            : {'Name': 'running'}    ,
            'Tags'             : [
                {'Key': 'StackName', 'Value': 'ff-quiet-fermi-1234'},
                {'Key': 'StackType', 'Value': 'firefox'             },
            ],
            'LaunchTime'       : None                   ,
        }
        info = p._raw_to_node_info(raw, 'eu-west-2', 'firefox')
        assert info.node_id       == 'ff-quiet-fermi-1234'
        assert info.spec_id       == 'firefox'
        assert info.state         == Enum__Node__State.READY
        assert info.public_ip     == '1.2.3.4'
        assert info.instance_id   == 'i-0abc123'

    def test_raw_to_node_info_pending(self):
        p   = EC2__Platform()
        raw = {
            'InstanceId'  : 'i-0def456'             ,
            'InstanceType': 't3.medium'              ,
            'ImageId'     : 'ami-0abc'               ,
            'State'       : {'Name': 'pending'}      ,
            'Tags'        : [{'Key': 'StackName', 'Value': 'test-node-0001'}],
            'LaunchTime'  : None                     ,
        }
        info = p._raw_to_node_info(raw, 'us-east-1')
        assert info.state == Enum__Node__State.BOOTING
