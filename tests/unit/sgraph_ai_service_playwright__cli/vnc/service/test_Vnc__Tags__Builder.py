# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Vnc__Tags__Builder
# Pure mapper — no AWS calls. Locks the N5 interceptor-tag values.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.vnc.enums.Enum__Vnc__Interceptor__Kind       import Enum__Vnc__Interceptor__Kind
from sgraph_ai_service_playwright__cli.vnc.schemas.Schema__Vnc__Interceptor__Choice import Schema__Vnc__Interceptor__Choice
from sgraph_ai_service_playwright__cli.vnc.service.Vnc__AWS__Client                 import (TAG_ALLOWED_IP_KEY    ,
                                                                                              TAG_CREATOR_KEY       ,
                                                                                              TAG_INTERCEPTOR_KEY   ,
                                                                                              TAG_INTERCEPTOR_NONE  ,
                                                                                              TAG_PURPOSE_KEY       ,
                                                                                              TAG_PURPOSE_VALUE     ,
                                                                                              TAG_SECTION_KEY       ,
                                                                                              TAG_SECTION_VALUE     ,
                                                                                              TAG_STACK_NAME_KEY    )
from sgraph_ai_service_playwright__cli.vnc.service.Vnc__Tags__Builder               import Vnc__Tags__Builder


class test_Vnc__Tags__Builder(TestCase):

    def setUp(self):
        self.builder = Vnc__Tags__Builder()

    def test_build__name_tag_carries_vnc_prefix(self):
        tags = self.builder.build('quiet-fermi', '1.2.3.4', 'tester@example.com')
        as_dict = {t['Key']: t['Value'] for t in tags}
        assert as_dict['Name'] == 'vnc-quiet-fermi'

    def test_build__name_tag_does_not_double_prefix(self):
        tags = self.builder.build('vnc-prod', '1.2.3.4', 'tester@example.com')
        as_dict = {t['Key']: t['Value'] for t in tags}
        assert as_dict['Name'] == 'vnc-prod'

    def test_build__includes_full_tag_set(self):
        tags = self.builder.build('vnc-foo', '1.2.3.4', 'tester@example.com')
        as_dict = {t['Key']: t['Value'] for t in tags}
        assert as_dict[TAG_PURPOSE_KEY]    == TAG_PURPOSE_VALUE
        assert as_dict[TAG_SECTION_KEY]    == TAG_SECTION_VALUE
        assert as_dict[TAG_STACK_NAME_KEY] == 'vnc-foo'
        assert as_dict[TAG_ALLOWED_IP_KEY] == '1.2.3.4'
        assert as_dict[TAG_CREATOR_KEY]    == 'tester@example.com'

    def test_build__creator_falls_back_to_unknown_when_empty(self):
        tags = self.builder.build('vnc-foo', '1.2.3.4', '')
        as_dict = {t['Key']: t['Value'] for t in tags}
        assert as_dict[TAG_CREATOR_KEY] == 'unknown'

    def test_build__interceptor_default_is_none(self):                              # No interceptor argument → kind=NONE → 'none'
        tags = self.builder.build('vnc-foo', '1.2.3.4', '')
        as_dict = {t['Key']: t['Value'] for t in tags}
        assert as_dict[TAG_INTERCEPTOR_KEY] == TAG_INTERCEPTOR_NONE

    def test_build__interceptor_name_tag_value(self):
        choice = Schema__Vnc__Interceptor__Choice(kind=Enum__Vnc__Interceptor__Kind.NAME, name='header_logger')
        tags   = self.builder.build('vnc-foo', '1.2.3.4', '', choice)
        as_dict = {t['Key']: t['Value'] for t in tags}
        assert as_dict[TAG_INTERCEPTOR_KEY] == 'name:header_logger'

    def test_build__interceptor_inline_tag_value(self):
        choice = Schema__Vnc__Interceptor__Choice(kind=Enum__Vnc__Interceptor__Kind.INLINE,
                                                    inline_source='from mitmproxy import http\n')
        tags   = self.builder.build('vnc-foo', '1.2.3.4', '', choice)
        as_dict = {t['Key']: t['Value'] for t in tags}
        assert as_dict[TAG_INTERCEPTOR_KEY] == 'inline'                              # Source itself never goes in a tag
