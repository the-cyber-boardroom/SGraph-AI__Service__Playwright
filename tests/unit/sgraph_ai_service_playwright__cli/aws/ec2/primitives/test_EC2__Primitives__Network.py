# ═══════════════════════════════════════════════════════════════════════════════
# Tests — EC2 Network Primitives
# Tests for Safe_Str__EC2__IGW_Id, Safe_Str__EC2__Route_Table_Id,
# Safe_Str__EC2__CIDR, Safe_Str__EC2__AZ.
# ═══════════════════════════════════════════════════════════════════════════════

import pytest

from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__AZ              import Safe_Str__EC2__AZ
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__CIDR            import Safe_Str__EC2__CIDR
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__IGW_Id          import Safe_Str__EC2__IGW_Id
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__Route_Table_Id  import Safe_Str__EC2__Route_Table_Id


class Test__Safe_Str__EC2__IGW_Id:

    def test_1__valid_short(self):
        v = Safe_Str__EC2__IGW_Id('igw-12345678')
        assert str(v) == 'igw-12345678'

    def test_2__valid_long(self):
        v = Safe_Str__EC2__IGW_Id('igw-0123456789abcdef0')
        assert str(v) == 'igw-0123456789abcdef0'

    def test_3__invalid_raises(self):
        with pytest.raises(Exception):
            Safe_Str__EC2__IGW_Id('not-an-igw')

    def test_4__empty_allowed(self):
        v = Safe_Str__EC2__IGW_Id('')
        assert str(v) == ''


class Test__Safe_Str__EC2__Route_Table_Id:

    def test_1__valid_short(self):
        v = Safe_Str__EC2__Route_Table_Id('rtb-12345678')
        assert str(v) == 'rtb-12345678'

    def test_2__valid_long(self):
        v = Safe_Str__EC2__Route_Table_Id('rtb-0123456789abcdef0')
        assert str(v) == 'rtb-0123456789abcdef0'

    def test_3__invalid_raises(self):
        with pytest.raises(Exception):
            Safe_Str__EC2__Route_Table_Id('not-a-rtb')

    def test_4__empty_allowed(self):
        v = Safe_Str__EC2__Route_Table_Id('')
        assert str(v) == ''


class Test__Safe_Str__EC2__CIDR:

    def test_1__valid_ipv4_cidr(self):
        v = Safe_Str__EC2__CIDR('10.0.0.0/16')
        assert str(v) == '10.0.0.0/16'

    def test_2__valid_full_ipv4(self):
        v = Safe_Str__EC2__CIDR('192.168.1.0/24')
        assert str(v) == '192.168.1.0/24'

    def test_3__invalid_no_prefix_raises(self):
        with pytest.raises(Exception):
            Safe_Str__EC2__CIDR('10.0.0.0')

    def test_4__empty_allowed(self):
        v = Safe_Str__EC2__CIDR('')
        assert str(v) == ''


class Test__Safe_Str__EC2__AZ:

    def test_1__valid_simple(self):
        v = Safe_Str__EC2__AZ('eu-west-2a')
        assert str(v) == 'eu-west-2a'

    def test_2__valid_long_region(self):
        v = Safe_Str__EC2__AZ('ap-northeast-1c')
        assert str(v) == 'ap-northeast-1c'

    def test_3__valid_no_letter_suffix(self):
        v = Safe_Str__EC2__AZ('us-east-1')                                       # matches \d optional letter pattern
        assert str(v) == 'us-east-1'

    def test_4__invalid_raises(self):
        with pytest.raises(Exception):
            Safe_Str__EC2__AZ('not-an-az!')

    def test_5__empty_allowed(self):
        v = Safe_Str__EC2__AZ('')
        assert str(v) == ''
