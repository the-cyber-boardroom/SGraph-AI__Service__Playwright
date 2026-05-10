# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Local_Claude__AMI__Helper
# ═══════════════════════════════════════════════════════════════════════════════

import pytest

from sg_compute_specs.local_claude.enums.Enum__Local_Claude__AMI__Base  import Enum__Local_Claude__AMI__Base
from sg_compute_specs.local_claude.service.Local_Claude__AMI__Helper     import (AL2023_SSM_PARAM           ,
                                                                                  Local_Claude__AMI__Helper  )


class TestLocalClaudeAMIHelper:

    def test_ssm_param_constants(self):
        assert 'al2023' in AL2023_SSM_PARAM.lower()

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
