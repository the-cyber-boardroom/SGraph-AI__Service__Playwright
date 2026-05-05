# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Firefox: tests for Firefox__Tags__Builder
# Pure mapper — no AWS calls.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sg_compute_specs.firefox.service.Firefox__Tags                                 import (FIREFOX_NAMING     ,
                                                                                             TAG_ALLOWED_IP_KEY ,
                                                                                             TAG_CREATOR_KEY    ,
                                                                                             TAG_PURPOSE_KEY    ,
                                                                                             TAG_PURPOSE_VALUE  ,
                                                                                             TAG_SECTION_KEY    ,
                                                                                             TAG_SECTION_VALUE  ,
                                                                                             TAG_STACK_NAME_KEY )
from sg_compute_specs.firefox.service.Firefox__Tags__Builder                        import Firefox__Tags__Builder


class test_Firefox__Tags__Builder(TestCase):

    def setUp(self):
        self.builder = Firefox__Tags__Builder()

    def test_build__name_tag_carries_firefox_prefix(self):
        tags    = self.builder.build('fast-fermi', '1.2.3.4', 'tester@example.com')
        as_dict = {t['Key']: t['Value'] for t in tags}
        assert as_dict['Name'] == 'firefox-fast-fermi'

    def test_build__name_tag_does_not_double_prefix(self):
        tags    = self.builder.build('firefox-fast-fermi', '1.2.3.4')
        as_dict = {t['Key']: t['Value'] for t in tags}
        assert as_dict['Name'] == 'firefox-fast-fermi'

    def test_build__includes_full_tag_set(self):
        tags    = self.builder.build('cool-newton', '10.0.0.1', 'dev@example.com')
        as_dict = {t['Key']: t['Value'] for t in tags}
        assert as_dict[TAG_PURPOSE_KEY]    == TAG_PURPOSE_VALUE
        assert as_dict[TAG_SECTION_KEY]    == TAG_SECTION_VALUE
        assert as_dict[TAG_STACK_NAME_KEY] == 'cool-newton'
        assert as_dict[TAG_ALLOWED_IP_KEY] == '10.0.0.1'
        assert as_dict[TAG_CREATOR_KEY]    == 'dev@example.com'

    def test_build__purpose_and_section_are_firefox(self):
        tags    = self.builder.build('fast-fermi', '1.2.3.4', '')
        as_dict = {t['Key']: t['Value'] for t in tags}
        assert as_dict[TAG_PURPOSE_KEY] == 'firefox'
        assert as_dict[TAG_SECTION_KEY] == 'firefox'

    def test_build__creator_defaults_to_unknown(self):
        tags    = self.builder.build('fast-fermi', '1.2.3.4')
        as_dict = {t['Key']: t['Value'] for t in tags}
        assert as_dict[TAG_CREATOR_KEY] == 'unknown'

    def test_build__sg_name_never_starts_with_sg_prefix(self):
        sg_name = FIREFOX_NAMING.sg_name_for_stack('fast-fermi')
        assert not sg_name.startswith('sg-')
        assert sg_name == 'fast-fermi-sg'

    def test_build__six_tags_total(self):
        tags = self.builder.build('fast-fermi', '1.2.3.4', 'dev')
        assert len(tags) == 6
