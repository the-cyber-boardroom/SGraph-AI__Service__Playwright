# ═══════════════════════════════════════════════════════════════════════════════
# Tests — EC2 Primitives
# Tests for Safe_Str__EC2__Instance_Id, Safe_Str__EC2__AMI_Id,
# Safe_Str__EC2__Instance__Type.
# ═══════════════════════════════════════════════════════════════════════════════

import pytest

from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__Instance_Id    import Safe_Str__EC2__Instance_Id
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__AMI_Id         import Safe_Str__EC2__AMI_Id
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__Instance__Type import Safe_Str__EC2__Instance__Type


class Test__Safe_Str__EC2__Instance_Id:

    def test_1__valid_8_char(self):
        iid = Safe_Str__EC2__Instance_Id('i-12345678')
        assert str(iid) == 'i-12345678'

    def test_2__valid_17_char(self):
        iid = Safe_Str__EC2__Instance_Id('i-12345678901234567')
        assert str(iid) == 'i-12345678901234567'

    def test_3__invalid_raises(self):
        with pytest.raises(Exception):
            Safe_Str__EC2__Instance_Id('not-an-id')

    def test_4__empty_allowed(self):
        iid = Safe_Str__EC2__Instance_Id('')
        assert str(iid) == ''


class Test__Safe_Str__EC2__AMI_Id:

    def test_1__valid_ami_id(self):
        ami = Safe_Str__EC2__AMI_Id('ami-12345678')
        assert str(ami) == 'ami-12345678'

    def test_2__alias_string(self):
        ami = Safe_Str__EC2__AMI_Id('ubuntu-22.04-arm64')
        assert str(ami) == 'ubuntu-22.04-arm64'

    def test_3__empty_allowed(self):
        ami = Safe_Str__EC2__AMI_Id('')
        assert str(ami) == ''


class Test__Safe_Str__EC2__Instance__Type:

    def test_1__valid_types(self):
        for t in ('t3.micro', 'm5.large', 't4g.nano', 'c6g.xlarge'):
            itype = Safe_Str__EC2__Instance__Type(t)
            assert str(itype) == t

    def test_2__invalid_raises(self):
        with pytest.raises(Exception):
            Safe_Str__EC2__Instance__Type('INVALID TYPE!')

    def test_3__empty_allowed(self):
        itype = Safe_Str__EC2__Instance__Type('')
        assert str(itype) == ''
