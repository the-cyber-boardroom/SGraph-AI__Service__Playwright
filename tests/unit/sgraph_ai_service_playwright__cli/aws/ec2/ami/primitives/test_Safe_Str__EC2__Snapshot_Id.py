# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Safe_Str__EC2__Snapshot_Id
# Accept / reject cases for the EBS snapshot ID primitive.
# ═══════════════════════════════════════════════════════════════════════════════

import pytest

from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__Snapshot_Id import Safe_Str__EC2__Snapshot_Id


class Test__Safe_Str__EC2__Snapshot_Id:

    def test_1__valid_8_char(self):
        snap = Safe_Str__EC2__Snapshot_Id('snap-12345678')
        assert str(snap) == 'snap-12345678'

    def test_2__valid_17_char(self):
        snap = Safe_Str__EC2__Snapshot_Id('snap-1234567890abcdef0')
        assert str(snap) == 'snap-1234567890abcdef0'

    def test_3__invalid_prefix_raises(self):
        with pytest.raises(Exception):
            Safe_Str__EC2__Snapshot_Id('vol-12345678')

    def test_4__invalid_chars_raises(self):
        with pytest.raises(Exception):
            Safe_Str__EC2__Snapshot_Id('snap-XYZ12345')

    def test_5__too_short_raises(self):
        with pytest.raises(Exception):
            Safe_Str__EC2__Snapshot_Id('snap-1234')

    def test_6__empty_allowed(self):
        snap = Safe_Str__EC2__Snapshot_Id('')
        assert str(snap) == ''
