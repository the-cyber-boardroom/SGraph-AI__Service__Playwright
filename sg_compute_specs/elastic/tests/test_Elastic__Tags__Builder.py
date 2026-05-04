# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Elastic: tests for Elastic__AWS__Client tags
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sg_compute_specs.elastic.service.Elastic__AWS__Client                          import (Elastic__AWS__Client ,
                                                                                             ELASTIC_NAMING      ,
                                                                                             TAG_ALLOWED_IP_KEY  ,
                                                                                             TAG_CREATOR_KEY     ,
                                                                                             TAG_PURPOSE_KEY     ,
                                                                                             TAG_PURPOSE_VALUE   ,
                                                                                             TAG_STACK_NAME_KEY  )


class test_Elastic__Tags__Builder(TestCase):

    def setUp(self):
        self.client = Elastic__AWS__Client()

    def test_build_tags__name_tag_carries_elastic_prefix(self):
        tags    = self.client.build_tags('cool-newton', '1.2.3.4', 'tester@example.com')
        as_dict = {t['Key']: t['Value'] for t in tags}
        assert as_dict['Name'] == 'elastic-cool-newton'

    def test_build_tags__does_not_double_prefix(self):
        tags    = self.client.build_tags('elastic-cool-newton', '1.2.3.4', '')
        as_dict = {t['Key']: t['Value'] for t in tags}
        assert as_dict['Name'] == 'elastic-cool-newton'

    def test_build_tags__includes_required_keys(self):
        tags    = self.client.build_tags('cool-newton', '10.0.0.1', 'dev@example.com')
        as_dict = {t['Key']: t['Value'] for t in tags}
        assert as_dict[TAG_PURPOSE_KEY]    == TAG_PURPOSE_VALUE
        assert as_dict[TAG_STACK_NAME_KEY] == 'cool-newton'
        assert as_dict[TAG_ALLOWED_IP_KEY] == '10.0.0.1'
        assert as_dict[TAG_CREATOR_KEY]    == 'dev@example.com'

    def test_build_tags__purpose_is_elastic(self):
        tags    = self.client.build_tags('x-stack', '1.2.3.4', '')
        as_dict = {t['Key']: t['Value'] for t in tags}
        assert as_dict[TAG_PURPOSE_KEY] == 'elastic'

    def test_sg_name_never_starts_with_sg_prefix(self):
        sg_name = ELASTIC_NAMING.sg_name_for_stack('cool-newton')
        assert not sg_name.startswith('sg-')
        assert sg_name == 'cool-newton-sg'
