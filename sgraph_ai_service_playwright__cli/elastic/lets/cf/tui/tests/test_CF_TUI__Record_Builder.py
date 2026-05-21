# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — cf tui: CF_TUI__Record_Builder
# Pins one TSV line → Schema__CF_TUI__Record_View: grouped fields, raw→transformed
# change flags, invalid handling, and the build_from_text line picker. No textual.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.Bot__Classifier        import Bot__Classifier
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.CF__Realtime__Log__Parser import CF__Realtime__Log__Parser
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.cf_tui__fixtures           import FIXTURE_TSV, LINE_ENHANCECP
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.service.CF_TUI__Record_Builder import CF_TUI__Record_Builder


def builder():
    return CF_TUI__Record_Builder(parser=CF__Realtime__Log__Parser(bot_classifier=Bot__Classifier()))


class test_CF_TUI__Record_Builder(TestCase):

    def setUp(self):
        self.view = builder().build(LINE_ENHANCECP, key='x/a.gz', line_index=0)

    def test_valid_and_groups(self):
        assert self.view.valid is True
        groups = {f.group for f in self.view.fields}
        assert groups == {'RAW', 'DERIVED', 'LINEAGE', 'PIPELINE'}
        raw = [f for f in self.view.fields if f.group == 'RAW']
        assert len(raw) == 26

    def fields_by_name(self):
        return {f.name: f for f in self.view.fields}

    def test_user_agent_changed_raw_to_decoded(self):
        ua = self.fields_by_name()['cs-user-agent']
        assert '%20'    in ua.raw                                                    # raw is URL-encoded
        assert '%20'    not in ua.value                                             # transformed is decoded
        assert ua.changed is True

    def test_unchanged_field_not_flagged(self):
        uri = self.fields_by_name()['cs-uri-stem']
        assert uri.raw == '/enhancecp' and uri.value == '/enhancecp'
        assert uri.changed is False

    def test_derived_present(self):
        f = self.fields_by_name()
        assert f['sc_status_class'].value == 'REDIRECTION' or '3' in f['sc_status_class'].value
        assert f['is_bot'].value == 'True'
        assert f['doc_id'].value.startswith('line-')

    def test_invalid_line(self):
        view = builder().build('not\ttab\tdelimited', key='x', line_index=0)
        assert view.valid is False
        assert view.column_count == 3

    def test_build_from_text_picks_line(self):
        view = builder().build_from_text(FIXTURE_TSV, key='x/a.gz', line_index=1)    # second valid line = /robots.txt
        assert view.valid is True
        uri = {f.name: f for f in view.fields}['cs-uri-stem']
        assert uri.value == '/robots.txt'

    def test_build_from_text_out_of_range(self):
        view = builder().build_from_text(FIXTURE_TSV, key='x', line_index=9)
        assert view.valid is False
