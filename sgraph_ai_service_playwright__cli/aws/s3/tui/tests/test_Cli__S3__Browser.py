# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — s3 tui: Cli__S3__Browser
# Tests the URI parser and the no-TTY listing (CliRunner-free: stdout is not a TTY in
# pytest, so run_browse takes the static-listing branch). Injects the fake source via
# the factory seam — no AWS, no mocks.
# ═══════════════════════════════════════════════════════════════════════════════

import io
from contextlib import redirect_stdout
from unittest   import TestCase

from sgraph_ai_service_playwright__cli.aws.s3.tui.cli import Cli__S3__Browser as mod
from sgraph_ai_service_playwright__cli.aws.s3.tui.tests.test_S3_Browser__Source import source


class test_parse_s3_uri(TestCase):

    def test_forms(self):
        assert mod.parse_s3_uri('')                  == ('', '')
        assert mod.parse_s3_uri('s3://bucket')        == ('bucket', '')
        assert mod.parse_s3_uri('s3://bucket/a/b')    == ('bucket', 'a/b')
        assert mod.parse_s3_uri('bucket/a')           == ('bucket', 'a')


class test_run_browse_no_tty(TestCase):

    def setUp(self):
        mod._source_factory = source

    def tearDown(self):
        mod._source_factory = None

    def test_root_lists_buckets(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            mod.run_browse('')
        out = buf.getvalue()
        assert 'S3 Browser' in out
        assert 'bucket-1'   in out

    def test_bucket_lists_dir(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            mod.run_browse('s3://b')
        out = buf.getvalue()
        assert 'logs/'  in out
        assert 'a.json' in out
