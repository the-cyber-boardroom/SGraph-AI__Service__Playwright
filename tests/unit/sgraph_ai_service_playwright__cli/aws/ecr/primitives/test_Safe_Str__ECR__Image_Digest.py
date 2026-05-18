# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Safe_Str__ECR__Image_Digest
# ═══════════════════════════════════════════════════════════════════════════════

import pytest

from sgraph_ai_service_playwright__cli.aws.ecr.primitives.Safe_Str__ECR__Image_Digest import Safe_Str__ECR__Image_Digest


_GOOD = 'sha256:' + 'a' * 64


class Test__Safe_Str__ECR__Image_Digest:

    def test_1__valid(self):
        assert str(Safe_Str__ECR__Image_Digest(_GOOD)) == _GOOD

    def test_2__empty_allowed(self):
        assert str(Safe_Str__ECR__Image_Digest('')) == ''

    def test_3__reject_missing_prefix(self):
        with pytest.raises(Exception):
            Safe_Str__ECR__Image_Digest('a' * 64)

    def test_4__reject_uppercase_hex(self):
        with pytest.raises(Exception):
            Safe_Str__ECR__Image_Digest('sha256:' + 'A' * 64)

    def test_5__reject_short_hex(self):
        with pytest.raises(Exception):
            Safe_Str__ECR__Image_Digest('sha256:' + 'a' * 63)
