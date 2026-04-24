# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Safe_Str__AWS__Region
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                                                   import TestCase
import pytest

from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Str__AWS__Region                           import Safe_Str__AWS__Region


class test_Safe_Str__AWS__Region(TestCase):

    def test__accepts_common_regions(self):
        assert str(Safe_Str__AWS__Region('eu-west-2'      )) == 'eu-west-2'
        assert str(Safe_Str__AWS__Region('us-east-1'      )) == 'us-east-1'
        assert str(Safe_Str__AWS__Region('ap-southeast-1' )) == 'ap-southeast-1'

    def test__allows_empty(self):                                                   # Empty = "resolve at runtime"
        assert str(Safe_Str__AWS__Region('')) == ''

    def test__rejects_bad_shape(self):
        with pytest.raises(ValueError):
            Safe_Str__AWS__Region('not-a-region')
        with pytest.raises(ValueError):
            Safe_Str__AWS__Region('eu_west_2')
