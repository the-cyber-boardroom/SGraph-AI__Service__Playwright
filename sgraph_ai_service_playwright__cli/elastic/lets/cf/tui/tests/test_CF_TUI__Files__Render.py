# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — cf tui: Files browser render (pure)
# Asserts the browse list (selection marker, count, no-files), the file view (parsed
# rows + raw toggle), the plain no-TTY listing, and human_size. No textual, no rich.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.Bot__Classifier        import Bot__Classifier
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.CF__Realtime__Log__Parser import CF__Realtime__Log__Parser
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.cf_tui__fixtures           import FIXTURE_TSV
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.schemas.List__CF_TUI__File_Row import List__CF_TUI__File_Row
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.schemas.Schema__CF_TUI__File_Row import Schema__CF_TUI__File_Row
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.service.CF_TUI__File_Builder import CF_TUI__File_Builder
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.screens.CF_TUI__Files__Render import files_browse_markup, files_browse_plain, file_view_markup, human_size


def rows():
    out = List__CF_TUI__File_Row()
    out.append(Schema__CF_TUI__File_Row(key='cloudfront-realtime/2026/04/21/08/a.gz', size_bytes=480,  delivery_iso='2026-04-21T08:00:01Z'))
    out.append(Schema__CF_TUI__File_Row(key='cloudfront-realtime/2026/04/21/08/b.gz', size_bytes=2048, delivery_iso='2026-04-21T08:00:02Z'))
    return out


def file_view():
    return CF_TUI__File_Builder(parser=CF__Realtime__Log__Parser(bot_classifier=Bot__Classifier())).build('a.gz', FIXTURE_TSV, size_bytes=480)


class test_files_browse(TestCase):

    def test_marker_count_and_basenames(self):
        out = files_browse_markup(rows(), selected_index=1, scope_label='s3://bucket/x')
        assert '(2)'   in out
        assert 'a.gz'  in out and 'b.gz' in out
        assert '▸'     in out                                                        # selection marker present

    def test_empty(self):
        out = files_browse_markup(List__CF_TUI__File_Row(), 0, 's3://bucket/x')
        assert '(no files)' in out

    def test_plain_no_markup(self):
        out = files_browse_plain(rows(), 's3://bucket/x')
        assert 'a.gz' in out
        assert '['    not in out                                                     # plain text — no Rich markup


class test_file_view(TestCase):

    def test_parsed_rows(self):
        out = file_view_markup(file_view(), raw=False)
        for token in ('a.gz', 'parsed', '/enhancecp', '/robots.txt', 'GET'):
            assert token in out, token

    def test_raw_toggle(self):
        out = file_view_markup(file_view(), raw=True)
        assert 'raw TSV' in out
        assert '/enhancecp' in out                                                   # raw line content shown


class test_human_size(TestCase):

    def test_units(self):
        assert human_size(512)            == '512B'
        assert human_size(2048).endswith('KB')
        assert human_size(5 * 1024 * 1024).endswith('MB')
