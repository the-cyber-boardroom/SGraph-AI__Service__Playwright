# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Prometheus__Tags__Builder
# Pure mapper — no AWS calls.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.prometheus.service.Prometheus__AWS__Client   import (TAG_ALLOWED_IP_KEY,
                                                                                              TAG_CREATOR_KEY   ,
                                                                                              TAG_PURPOSE_KEY   ,
                                                                                              TAG_PURPOSE_VALUE ,
                                                                                              TAG_SECTION_KEY   ,
                                                                                              TAG_SECTION_VALUE ,
                                                                                              TAG_STACK_NAME_KEY)
from sgraph_ai_service_playwright__cli.prometheus.service.Prometheus__Tags__Builder import Prometheus__Tags__Builder


class test_Prometheus__Tags__Builder(TestCase):

    def setUp(self):
        self.builder = Prometheus__Tags__Builder()

    def test_build__name_tag_carries_prometheus_prefix(self):
        tags = self.builder.build('quiet-fermi', '1.2.3.4', 'tester@example.com')
        as_dict = {t['Key']: t['Value'] for t in tags}
        assert as_dict['Name'] == 'prometheus-quiet-fermi'                            # PROM_NAMING.aws_name_for_stack adds prefix when missing

    def test_build__name_tag_does_not_double_prefix(self):                            # Already-prefixed stack name stays unchanged
        tags = self.builder.build('prometheus-prod', '1.2.3.4', 'tester@example.com')
        as_dict = {t['Key']: t['Value'] for t in tags}
        assert as_dict['Name'] == 'prometheus-prod'

    def test_build__includes_full_tag_set(self):
        tags = self.builder.build('prom-foo', '1.2.3.4', 'tester@example.com')
        as_dict = {t['Key']: t['Value'] for t in tags}
        assert as_dict[TAG_PURPOSE_KEY]    == TAG_PURPOSE_VALUE
        assert as_dict[TAG_SECTION_KEY]    == TAG_SECTION_VALUE
        assert as_dict[TAG_STACK_NAME_KEY] == 'prom-foo'
        assert as_dict[TAG_ALLOWED_IP_KEY] == '1.2.3.4'
        assert as_dict[TAG_CREATOR_KEY]    == 'tester@example.com'

    def test_build__creator_falls_back_to_unknown_when_empty(self):
        tags = self.builder.build('prom-foo', '1.2.3.4', '')
        as_dict = {t['Key']: t['Value'] for t in tags}
        assert as_dict[TAG_CREATOR_KEY] == 'unknown'
