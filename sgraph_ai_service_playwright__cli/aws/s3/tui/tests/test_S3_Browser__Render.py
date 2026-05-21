# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — s3 tui: S3_Browser__Render (pure)
# Asserts the entry list markup/plain and the object preview. No textual, no rich.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright__cli.aws.s3.tui.schemas.List__S3_Browser__Entry import List__S3_Browser__Entry
from sgraph_ai_service_playwright__cli.aws.s3.tui.schemas.Schema__S3_Browser__Entry import Schema__S3_Browser__Entry
from sgraph_ai_service_playwright__cli.aws.s3.tui.schemas.Schema__S3_Browser__View  import Schema__S3_Browser__View
from sgraph_ai_service_playwright__cli.aws.s3.tui.screens.S3_Browser__Render import entries_markup, entries_plain, object_markup, human_size


def entries():
    out = List__S3_Browser__Entry()
    out.append(Schema__S3_Browser__Entry(name='logs/',  kind='folder', bucket='b', path='logs/'))
    out.append(Schema__S3_Browser__Entry(name='a.json', kind='file',   bucket='b', path='a.json', size_bytes=2048, last_modified='2026-05-21'))
    return out


class test_entries(TestCase):

    def test_markup(self):
        out = entries_markup(entries(), selected_index=1, title='s3://b/')
        for token in ('S3 Browser', 's3://b/', 'logs/', 'a.json', 'folder', '▸'):
            assert token in out, token

    def test_empty(self):
        assert '(empty)' in entries_markup(List__S3_Browser__Entry(), 0, 's3://')

    def test_plain(self):
        out = entries_plain(entries(), 's3://b/')
        assert 'logs/' in out and 'a.json' in out
        assert '['     not in out


class test_object_markup(TestCase):

    def test_text(self):
        view = Schema__S3_Browser__View(bucket='b', key='logs/x.gz', size_bytes=40, fmt='text', text='line-1\nline-2', gunzipped=True)
        out  = object_markup(view)
        assert 'logs/x.gz' in out
        assert 'gunzipped' in out
        assert 'line-1'    in out


class test_human_size(TestCase):

    def test_units(self):
        assert human_size(512) == '512B'
        assert human_size(2048).endswith('KB')
