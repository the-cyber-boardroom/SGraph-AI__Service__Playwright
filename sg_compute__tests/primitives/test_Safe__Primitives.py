# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute tests — Safe_* primitives (T2.6)
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

import pytest

from sg_compute.primitives.Safe_Int__Hours            import Safe_Int__Hours
from sg_compute.primitives.Safe_Int__Port             import Safe_Int__Port
from sg_compute.primitives.Safe_Int__Uptime__Seconds  import Safe_Int__Uptime__Seconds
from sg_compute.primitives.Safe_Str__IP__Address      import Safe_Str__IP__Address
from sg_compute.primitives.Safe_Str__Image__Registry  import Safe_Str__Image__Registry
from sg_compute.primitives.Safe_Str__Image__Tag       import Safe_Str__Image__Tag
from sg_compute.primitives.Safe_Str__Instance__Type   import Safe_Str__Instance__Type
from sg_compute.primitives.Safe_Str__Message          import Safe_Str__Message
from sg_compute.primitives.Safe_Str__Node__Name       import Safe_Str__Node__Name
from sg_compute.primitives.Safe_Str__SG__Id           import Safe_Str__SG__Id
from sg_compute.primitives.Safe_Str__SSM__Path        import Safe_Str__SSM__Path
from sg_compute.primitives.Safe_Str__Stack__Name      import Safe_Str__Stack__Name


class test_Safe_Int__Port(TestCase):

    def test_valid(self):
        assert int(Safe_Int__Port(80))    == 80
        assert int(Safe_Int__Port(443))   == 443
        assert int(Safe_Int__Port(19009)) == 19009
        assert int(Safe_Int__Port(1))     == 1
        assert int(Safe_Int__Port(65535)) == 65535

    def test_below_min_raises(self):
        with pytest.raises((ValueError, Exception)):
            Safe_Int__Port(0)

    def test_above_max_raises(self):
        with pytest.raises((ValueError, Exception)):
            Safe_Int__Port(65536)


class test_Safe_Int__Hours(TestCase):

    def test_valid(self):
        assert int(Safe_Int__Hours(1))   == 1
        assert int(Safe_Int__Hours(24))  == 24
        assert int(Safe_Int__Hours(168)) == 168

    def test_below_min_raises(self):
        with pytest.raises((ValueError, Exception)):
            Safe_Int__Hours(0)

    def test_above_max_raises(self):
        with pytest.raises((ValueError, Exception)):
            Safe_Int__Hours(169)


class test_Safe_Int__Uptime__Seconds(TestCase):

    def test_valid(self):
        assert int(Safe_Int__Uptime__Seconds(0))   == 0
        assert int(Safe_Int__Uptime__Seconds(300)) == 300

    def test_negative_raises(self):
        with pytest.raises((ValueError, Exception)):
            Safe_Int__Uptime__Seconds(-1)


class test_Safe_Str__IP__Address(TestCase):

    def test_valid_ipv4(self):
        assert str(Safe_Str__IP__Address('1.2.3.4'))    == '1.2.3.4'
        assert str(Safe_Str__IP__Address('10.0.0.1'))   == '10.0.0.1'
        assert str(Safe_Str__IP__Address('192.168.1.1'))== '192.168.1.1'

    def test_empty_allowed(self):
        assert str(Safe_Str__IP__Address()) == ''

    def test_ipv6_allowed(self):
        assert str(Safe_Str__IP__Address('::1')) == '::1'


class test_Safe_Str__Image__Registry(TestCase):

    def test_valid(self):
        r = '123456789.dkr.ecr.eu-west-2.amazonaws.com'
        assert str(Safe_Str__Image__Registry(r)) == r

    def test_empty_allowed(self):
        assert str(Safe_Str__Image__Registry()) == ''


class test_Safe_Str__Image__Tag(TestCase):

    def test_valid(self):
        assert str(Safe_Str__Image__Tag('latest'))  == 'latest'
        assert str(Safe_Str__Image__Tag('v1.2.3'))  == 'v1.2.3'
        assert str(Safe_Str__Image__Tag('sha-abc')) == 'sha-abc'

    def test_empty_allowed(self):
        assert str(Safe_Str__Image__Tag()) == ''


class test_Safe_Str__Instance__Type(TestCase):

    def test_valid(self):
        assert str(Safe_Str__Instance__Type('t3.large'))   == 't3.large'
        assert str(Safe_Str__Instance__Type('m5.xlarge'))  == 'm5.xlarge'
        assert str(Safe_Str__Instance__Type('c6i.2xlarge'))== 'c6i.2xlarge'

    def test_empty_allowed(self):
        assert str(Safe_Str__Instance__Type()) == ''


class test_Safe_Str__Message(TestCase):

    def test_valid(self):
        assert str(Safe_Str__Message('hello_world')) == 'hello_world'
        assert str(Safe_Str__Message('node_ready'))  == 'node_ready'

    def test_empty_allowed(self):
        assert str(Safe_Str__Message()) == ''

    def test_long_message_raises(self):
        with pytest.raises((ValueError, Exception)):
            Safe_Str__Message('x' * 513)


class test_Safe_Str__Node__Name(TestCase):

    def test_valid(self):
        assert str(Safe_Str__Node__Name('firefox-quiet-fermi-7421')) == 'firefox-quiet-fermi-7421'
        assert str(Safe_Str__Node__Name('node-1'))                   == 'node-1'

    def test_empty_allowed(self):
        assert str(Safe_Str__Node__Name()) == ''

    def test_uppercase_rejected(self):
        with pytest.raises((ValueError, Exception)):
            Safe_Str__Node__Name('Node-1')

    def test_starts_with_digit_rejected(self):
        with pytest.raises((ValueError, Exception)):
            Safe_Str__Node__Name('1node')


class test_Safe_Str__SG__Id(TestCase):

    def test_valid(self):
        assert str(Safe_Str__SG__Id('sg-0abc123'))           == 'sg-0abc123'
        assert str(Safe_Str__SG__Id('sg-0123456789abcdef0')) == 'sg-0123456789abcdef0'

    def test_empty_allowed(self):
        assert str(Safe_Str__SG__Id()) == ''

    def test_wrong_prefix_rejected(self):
        with pytest.raises((ValueError, Exception)):
            Safe_Str__SG__Id('vpc-0abc123')


class test_Safe_Str__SSM__Path(TestCase):

    def test_valid(self):
        p = '/sg-compute/nodes/my-node/sidecar-api-key'
        assert str(Safe_Str__SSM__Path(p)) == p

    def test_empty_allowed(self):
        assert str(Safe_Str__SSM__Path()) == ''


class test_Safe_Str__Stack__Name(TestCase):

    def test_valid(self):
        assert str(Safe_Str__Stack__Name('quiet-fermi'))      == 'quiet-fermi'
        assert str(Safe_Str__Stack__Name('docker-test-0001')) == 'docker-test-0001'

    def test_empty_allowed(self):
        assert str(Safe_Str__Stack__Name()) == ''

    def test_uppercase_rejected(self):
        with pytest.raises((ValueError, Exception)):
            Safe_Str__Stack__Name('Quiet-Fermi')
