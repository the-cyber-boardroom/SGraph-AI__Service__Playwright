# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — OpenSearch: tests for OpenSearch__Tags__Builder
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sg_compute_specs.opensearch.service.OpenSearch__AWS__Client                    import (TAG_ALLOWED_IP_KEY ,
                                                                                             TAG_CREATOR_KEY    ,
                                                                                             TAG_PURPOSE_KEY    ,
                                                                                             TAG_PURPOSE_VALUE  ,
                                                                                             TAG_SECTION_KEY    ,
                                                                                             TAG_SECTION_VALUE  ,
                                                                                             TAG_STACK_NAME_KEY ,
                                                                                             OS_NAMING          )
from sg_compute_specs.opensearch.service.OpenSearch__Tags__Builder                  import OpenSearch__Tags__Builder


class test_OpenSearch__Tags__Builder(TestCase):

    def setUp(self):
        self.builder = OpenSearch__Tags__Builder()

    def test_build__name_tag_carries_opensearch_prefix(self):
        tags    = self.builder.build('cool-newton', '1.2.3.4', 'tester@example.com')
        as_dict = {t['Key']: t['Value'] for t in tags}
        assert as_dict['Name'] == 'opensearch-cool-newton'

    def test_build__name_tag_does_not_double_prefix(self):
        tags    = self.builder.build('opensearch-cool-newton', '1.2.3.4')
        as_dict = {t['Key']: t['Value'] for t in tags}
        assert as_dict['Name'] == 'opensearch-cool-newton'

    def test_build__includes_full_tag_set(self):
        tags    = self.builder.build('cool-newton', '10.0.0.1', 'dev@example.com')
        as_dict = {t['Key']: t['Value'] for t in tags}
        assert as_dict[TAG_PURPOSE_KEY]    == TAG_PURPOSE_VALUE
        assert as_dict[TAG_SECTION_KEY]    == TAG_SECTION_VALUE
        assert as_dict[TAG_STACK_NAME_KEY] == 'cool-newton'
        assert as_dict[TAG_ALLOWED_IP_KEY] == '10.0.0.1'
        assert as_dict[TAG_CREATOR_KEY]    == 'dev@example.com'

    def test_build__purpose_is_opensearch_section_is_os(self):
        tags    = self.builder.build('x-foo', '1.2.3.4', '')
        as_dict = {t['Key']: t['Value'] for t in tags}
        assert as_dict[TAG_PURPOSE_KEY] == 'opensearch'
        assert as_dict[TAG_SECTION_KEY] == 'os'

    def test_build__sg_name_never_starts_with_sg_prefix(self):
        sg_name = OS_NAMING.sg_name_for_stack('cool-newton')
        assert not sg_name.startswith('sg-')
        assert sg_name == 'cool-newton-sg'
