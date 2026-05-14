# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Playwright__Tags__Builder
# Pure mapper — no AWS calls. Exercises the tag list including the
# sg:with-mitmproxy flag.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                    import TestCase

from sgraph_ai_service_playwright__cli.playwright.service.Playwright__AWS__Client    import (TAG_PURPOSE_KEY, TAG_PURPOSE_VALUE,
                                                                                              TAG_SECTION_KEY, TAG_SECTION_VALUE,
                                                                                              TAG_STACK_NAME_KEY, TAG_ALLOWED_IP_KEY,
                                                                                              TAG_CREATOR_KEY, TAG_WITH_MITMPROXY_KEY,
                                                                                              PLAYWRIGHT_NAMING)
from sgraph_ai_service_playwright__cli.playwright.service.Playwright__Tags__Builder  import Playwright__Tags__Builder


def _tags_as_dict(tags):
    return {t['Key']: t['Value'] for t in tags}


class test_Playwright__Tags__Builder(TestCase):

    def setUp(self):
        self.builder = Playwright__Tags__Builder()

    def test__build__contains_all_required_keys(self):
        tags = self.builder.build('playwright-quiet-fermi', '1.2.3.4', 'alice@example.com')
        d    = _tags_as_dict(tags)
        assert 'Name'              in d
        assert TAG_PURPOSE_KEY     in d
        assert TAG_SECTION_KEY     in d
        assert TAG_STACK_NAME_KEY  in d
        assert TAG_ALLOWED_IP_KEY  in d
        assert TAG_CREATOR_KEY     in d
        assert TAG_WITH_MITMPROXY_KEY in d

    def test__build__name_tag_carries_playwright_prefix(self):
        tags = self.builder.build('quiet-fermi', '1.2.3.4')
        d    = _tags_as_dict(tags)
        assert d['Name'] == 'playwright-quiet-fermi'

    def test__build__name_tag_not_doubled_when_prefix_present(self):
        tags = self.builder.build('playwright-quiet-fermi', '1.2.3.4')
        d    = _tags_as_dict(tags)
        assert d['Name'] == 'playwright-quiet-fermi'                             # no double prefix

    def test__build__purpose_and_section_values(self):
        tags = self.builder.build('s', '1.2.3.4')
        d    = _tags_as_dict(tags)
        assert d[TAG_PURPOSE_KEY] == TAG_PURPOSE_VALUE
        assert d[TAG_SECTION_KEY] == TAG_SECTION_VALUE

    def test__build__stack_name_and_allowed_ip(self):
        tags = self.builder.build('playwright-abc', '9.8.7.6', 'bob@example.com')
        d    = _tags_as_dict(tags)
        assert d[TAG_STACK_NAME_KEY] == 'playwright-abc'
        assert d[TAG_ALLOWED_IP_KEY] == '9.8.7.6'
        assert d[TAG_CREATOR_KEY]    == 'bob@example.com'

    def test__build__with_mitmproxy_false(self):
        tags = self.builder.build('s', '1.2.3.4', with_mitmproxy=False)
        d    = _tags_as_dict(tags)
        assert d[TAG_WITH_MITMPROXY_KEY] == 'false'

    def test__build__with_mitmproxy_true(self):
        tags = self.builder.build('s', '1.2.3.4', with_mitmproxy=True)
        d    = _tags_as_dict(tags)
        assert d[TAG_WITH_MITMPROXY_KEY] == 'true'

    def test__build__creator_defaults_to_unknown_when_empty(self):
        tags = self.builder.build('s', '1.2.3.4')
        d    = _tags_as_dict(tags)
        assert d[TAG_CREATOR_KEY] == 'unknown'
