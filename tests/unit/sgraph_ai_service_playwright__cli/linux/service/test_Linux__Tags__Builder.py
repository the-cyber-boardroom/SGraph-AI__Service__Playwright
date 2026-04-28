# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Linux__Tags__Builder
# Pure mapper — no AWS calls.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.linux.service.Linux__AWS__Client             import (TAG_ALLOWED_IP_KEY,
                                                                                              TAG_CREATOR_KEY   ,
                                                                                              TAG_PURPOSE_KEY   ,
                                                                                              TAG_PURPOSE_VALUE ,
                                                                                              TAG_SECTION_KEY   ,
                                                                                              TAG_SECTION_VALUE ,
                                                                                              TAG_STACK_NAME_KEY)
from sgraph_ai_service_playwright__cli.linux.service.Linux__Tags__Builder           import Linux__Tags__Builder


class test_Linux__Tags__Builder(TestCase):

    def setUp(self):
        self.builder = Linux__Tags__Builder()

    def test_build__name_tag_carries_linux_prefix(self):
        tags    = self.builder.build('happy-turing', '1.2.3.4', 'tester@example.com')
        as_dict = {t['Key']: t['Value'] for t in tags}
        assert as_dict['Name'] == 'linux-happy-turing'

    def test_build__name_tag_does_not_double_prefix(self):
        tags    = self.builder.build('linux-happy-turing', '1.2.3.4')
        as_dict = {t['Key']: t['Value'] for t in tags}
        assert as_dict['Name'] == 'linux-happy-turing'

    def test_build__includes_full_tag_set(self):
        tags    = self.builder.build('bold-newton', '10.0.0.1', 'dev@example.com')
        as_dict = {t['Key']: t['Value'] for t in tags}
        assert as_dict[TAG_PURPOSE_KEY]    == TAG_PURPOSE_VALUE
        assert as_dict[TAG_SECTION_KEY]    == TAG_SECTION_VALUE
        assert as_dict[TAG_STACK_NAME_KEY] == 'bold-newton'
        assert as_dict[TAG_ALLOWED_IP_KEY] == '10.0.0.1'
        assert as_dict[TAG_CREATOR_KEY]    == 'dev@example.com'

    def test_build__creator_falls_back_to_unknown_when_empty(self):
        tags    = self.builder.build('x-foo', '1.2.3.4', '')
        as_dict = {t['Key']: t['Value'] for t in tags}
        assert as_dict[TAG_CREATOR_KEY] == 'unknown'

    def test_build__sg_name_never_starts_with_sg_prefix(self):                     # AWS rejects GroupName starting with 'sg-'
        from sgraph_ai_service_playwright__cli.linux.service.Linux__AWS__Client import LINUX_NAMING
        sg_name = LINUX_NAMING.sg_name_for_stack('happy-turing')
        assert not sg_name.startswith('sg-'), f'SG name {sg_name!r} must not start with sg-'
        assert sg_name == 'happy-turing-sg'
