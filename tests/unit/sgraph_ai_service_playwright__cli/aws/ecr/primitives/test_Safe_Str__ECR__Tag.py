# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Safe_Str__ECR__Tag
# ═══════════════════════════════════════════════════════════════════════════════

import pytest

from sgraph_ai_service_playwright__cli.aws.ecr.primitives.Safe_Str__ECR__Tag import Safe_Str__ECR__Tag


class Test__Safe_Str__ECR__Tag:

    def test_1__valid_simple(self):
        assert str(Safe_Str__ECR__Tag('v1')) == 'v1'

    def test_2__valid_with_dots_and_dashes(self):
        assert str(Safe_Str__ECR__Tag('v1.2.3-rc1')) == 'v1.2.3-rc1'

    def test_3__valid_single_word_char(self):
        assert str(Safe_Str__ECR__Tag('a')) == 'a'

    def test_4__empty_allowed(self):
        assert str(Safe_Str__ECR__Tag('')) == ''

    def test_5__reject_leading_dot(self):
        with pytest.raises(Exception):
            Safe_Str__ECR__Tag('.bad')

    def test_6__reject_leading_dash(self):
        with pytest.raises(Exception):
            Safe_Str__ECR__Tag('-bad')

    def test_7__reject_too_long(self):
        with pytest.raises(Exception):
            Safe_Str__ECR__Tag('a' * 129)
