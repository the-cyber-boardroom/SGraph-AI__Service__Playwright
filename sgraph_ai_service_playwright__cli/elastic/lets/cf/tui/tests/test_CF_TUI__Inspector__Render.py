# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — cf tui: Field Lineage Inspector render (pure)
# Asserts the inspector markup (groups, raw→value, transform chain), the invalid
# path, and the plain variant. No textual, no rich.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.Bot__Classifier        import Bot__Classifier
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.CF__Realtime__Log__Parser import CF__Realtime__Log__Parser
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.cf_tui__fixtures           import LINE_ENHANCECP
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.service.CF_TUI__Record_Builder import CF_TUI__Record_Builder
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.screens.CF_TUI__Inspector__Render import inspector_markup, inspector_plain


def view(line=LINE_ENHANCECP):
    return CF_TUI__Record_Builder(parser=CF__Realtime__Log__Parser(bot_classifier=Bot__Classifier())).build(line, key='x/a.gz', line_index=0)


class test_inspector_markup(TestCase):

    def test_groups_and_chain(self):
        out = inspector_markup(view())
        for token in ('Field Lineage', 'RAW', 'DERIVED', 'LINEAGE', 'PIPELINE',
                      'cs-user-agent', 'transform:', '/enhancecp'):
            assert token in out, token

    def test_changed_field_shows_arrow(self):
        out = inspector_markup(view())
        assert '→' in out                                                            # at least one raw→transformed row

    def test_invalid(self):
        bad = CF_TUI__Record_Builder(parser=CF__Realtime__Log__Parser(bot_classifier=Bot__Classifier())).build('a\tb', key='x')
        out = inspector_markup(bad)
        assert 'could not parse' in out


class test_inspector_plain(TestCase):

    def test_no_markup(self):
        out = inspector_plain(view())
        assert 'Field Lineage' in out
        assert 'cs-user-agent' in out
        assert '['             not in out                                            # plain — no Rich markup
