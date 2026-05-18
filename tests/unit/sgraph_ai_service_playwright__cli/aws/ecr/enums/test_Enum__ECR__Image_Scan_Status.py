# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Enum__ECR__Image_Scan_Status
# ═══════════════════════════════════════════════════════════════════════════════

import pytest

from sgraph_ai_service_playwright__cli.aws.ecr.enums.Enum__ECR__Image_Scan_Status import Enum__ECR__Image_Scan_Status


class Test__Enum__ECR__Image_Scan_Status:

    def test_1__members(self):
        names = {m.name for m in Enum__ECR__Image_Scan_Status}
        assert names == {'IN_PROGRESS', 'COMPLETE', 'FAILED', 'UNKNOWN'}

    def test_2__str_returns_value(self):
        assert str(Enum__ECR__Image_Scan_Status.COMPLETE)    == 'COMPLETE'
        assert str(Enum__ECR__Image_Scan_Status.IN_PROGRESS) == 'IN_PROGRESS'

    def test_3__unknown_value_raises(self):
        with pytest.raises(ValueError):
            Enum__ECR__Image_Scan_Status('NOT_A_REAL_STATUS')
