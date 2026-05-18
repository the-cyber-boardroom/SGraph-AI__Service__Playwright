# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Safe_Str__EC2__ENI_Id
# Accept / reject cases for the Elastic Network Interface ID primitive.
# ═══════════════════════════════════════════════════════════════════════════════

import pytest

from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__ENI_Id import Safe_Str__EC2__ENI_Id


class Test__Safe_Str__EC2__ENI_Id:

    def test_1__valid_8_char(self):
        eni = Safe_Str__EC2__ENI_Id('eni-12345678')
        assert str(eni) == 'eni-12345678'

    def test_2__valid_17_char(self):
        eni = Safe_Str__EC2__ENI_Id('eni-1234567890abcdef0')
        assert str(eni) == 'eni-1234567890abcdef0'

    def test_3__invalid_prefix_raises(self):
        with pytest.raises(Exception):
            Safe_Str__EC2__ENI_Id('sg-12345678')

    def test_4__invalid_chars_raises(self):
        with pytest.raises(Exception):
            Safe_Str__EC2__ENI_Id('eni-XYZ12345')

    def test_5__too_short_raises(self):
        with pytest.raises(Exception):
            Safe_Str__EC2__ENI_Id('eni-1234')

    def test_6__empty_allowed(self):
        eni = Safe_Str__EC2__ENI_Id('')
        assert str(eni) == ''
