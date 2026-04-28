# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Random__Stack__Name__Generator (linux-local)
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.linux.service.Random__Stack__Name__Generator import (ADJECTIVES,
                                                                                               Random__Stack__Name__Generator,
                                                                                               SCIENTISTS)


class test_Random__Stack__Name__Generator(TestCase):

    def test__shape_is_adjective_dash_scientist(self):
        gen = Random__Stack__Name__Generator()
        for _ in range(20):
            name = gen.generate()
            adjective, scientist = name.split('-')
            assert adjective in ADJECTIVES
            assert scientist in SCIENTISTS

    def test__lowercase_no_whitespace(self):
        gen = Random__Stack__Name__Generator()
        for _ in range(10):
            name = gen.generate()
            assert name == name.lower()
            assert ' ' not in name

    def test__pools_match_opensearch(self):                                         # Sister sections share vocabulary by design
        from sgraph_ai_service_playwright__cli.opensearch.service.Random__Stack__Name__Generator import (ADJECTIVES as OS_ADJ,
                                                                                                           SCIENTISTS as OS_SCI)
        assert ADJECTIVES == OS_ADJ
        assert SCIENTISTS == OS_SCI
