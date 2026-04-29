# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Random__Stack__Name__Generator (vnc-local)
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.vnc.service.Random__Stack__Name__Generator   import (ADJECTIVES,
                                                                                              Random__Stack__Name__Generator,
                                                                                              SCIENTISTS)


class test_Random__Stack__Name__Generator(TestCase):

    def test__shape_is_adjective_dash_scientist(self):
        gen = Random__Stack__Name__Generator()
        for _ in range(20):
            adjective, scientist = gen.generate().split('-')
            assert adjective in ADJECTIVES
            assert scientist in SCIENTISTS

    def test__pools_match_other_sister_sections(self):
        from sgraph_ai_service_playwright__cli.elastic.service.Elastic__Service          import ADJECTIVES as E_ADJ, SCIENTISTS as E_SCI
        from sgraph_ai_service_playwright__cli.opensearch.service.Random__Stack__Name__Generator import ADJECTIVES as O_ADJ, SCIENTISTS as O_SCI
        from sgraph_ai_service_playwright__cli.prometheus.service.Random__Stack__Name__Generator import ADJECTIVES as P_ADJ, SCIENTISTS as P_SCI
        assert ADJECTIVES == E_ADJ == O_ADJ == P_ADJ
        assert SCIENTISTS == E_SCI == O_SCI == P_SCI
