# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Local_Claude__AMI__Helper
# ═══════════════════════════════════════════════════════════════════════════════

import pytest

from sg_compute_specs.local_claude.enums.Enum__Local_Claude__AMI__Base  import Enum__Local_Claude__AMI__Base
from sg_compute_specs.local_claude.service.Local_Claude__AMI__Helper     import (AL2023_SSM_PARAM           ,
                                                                                  DLAMI_NAME_FILTER          ,
                                                                                  Local_Claude__AMI__Helper  )


class TestLocalClaudeAMIHelper:

    def test_ssm_param_constants(self):
        assert 'al2023' in AL2023_SSM_PARAM.lower()

    def test_dlami_name_filter_contains_al2023(self):
        assert 'Amazon Linux 2023' in DLAMI_NAME_FILTER
        assert 'Nvidia Driver'     in DLAMI_NAME_FILTER

    def test_resolve_for_base_dlami_dispatches(self, monkeypatch):
        helper = Local_Claude__AMI__Helper()
        calls  = []

        def fake_latest_dlami(region):
            calls.append(('dlami', region))
            return 'ami-dlami-fake'

        monkeypatch.setattr(helper, 'latest_dlami', fake_latest_dlami)
        result = helper.resolve_for_base('eu-west-2', Enum__Local_Claude__AMI__Base.DLAMI)
        assert result == 'ami-dlami-fake'
        assert calls  == [('dlami', 'eu-west-2')]

    def test_resolve_for_base_al2023_dispatches(self, monkeypatch):
        helper = Local_Claude__AMI__Helper()
        calls  = []

        def fake_latest_al2023(region):
            calls.append(('al2023', region))
            return 'ami-al2023-fake'

        monkeypatch.setattr(helper, 'latest_al2023', fake_latest_al2023)
        result = helper.resolve_for_base('eu-west-2', Enum__Local_Claude__AMI__Base.AL2023)
        assert result == 'ami-al2023-fake'
        assert calls  == [('al2023', 'eu-west-2')]

    def test_resolve_for_base_unknown_raises(self):
        helper = Local_Claude__AMI__Helper()
        with pytest.raises(ValueError, match='unknown AMI base'):
            helper.resolve_for_base('eu-west-2', 'not-a-valid-base')
