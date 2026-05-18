# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Safe_Str__ECR__Repo_Name
# ═══════════════════════════════════════════════════════════════════════════════

import pytest

from sgraph_ai_service_playwright__cli.aws.ecr.primitives.Safe_Str__ECR__Repo_Name import Safe_Str__ECR__Repo_Name


class Test__Safe_Str__ECR__Repo_Name:

    def test_1__valid_simple(self):
        assert str(Safe_Str__ECR__Repo_Name('myapp')) == 'myapp'

    def test_2__valid_with_namespace(self):
        assert str(Safe_Str__ECR__Repo_Name('team/myapp')) == 'team/myapp'

    def test_3__valid_with_dots_and_dashes(self):
        assert str(Safe_Str__ECR__Repo_Name('my-app.v2')) == 'my-app.v2'

    def test_4__empty_allowed(self):
        assert str(Safe_Str__ECR__Repo_Name('')) == ''

    def test_5__reject_uppercase(self):
        with pytest.raises(Exception):
            Safe_Str__ECR__Repo_Name('MyApp')

    def test_6__reject_leading_hyphen(self):
        with pytest.raises(Exception):
            Safe_Str__ECR__Repo_Name('-bad')

    def test_7__reject_single_char(self):
        with pytest.raises(Exception):
            Safe_Str__ECR__Repo_Name('a')                                       # regex requires >= 2 chars
