# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — cf tui: architecture render (pure)
# Asserts the wiring markup + plain variant, the UNVERIFIED markers, and the error
# line. No textual, no rich.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.schemas.Schema__CF_TUI__Arch_Distribution import Schema__CF_TUI__Arch_Distribution
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.schemas.Schema__CF_TUI__Arch_Snapshot      import Schema__CF_TUI__Arch_Snapshot
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.screens.CF_TUI__Arch__Render import arch_markup, arch_plain


def snap():
    s = Schema__CF_TUI__Arch_Snapshot(captured_at=100, bucket_name='cf-logs-bucket', bucket_reachable=True, bucket_top_folders=1)
    s.distributions.append(Schema__CF_TUI__Arch_Distribution(distribution_id='E1ABC', domain='d1.cloudfront.net', aliases='sgraph.ai', status='Deployed'))
    return s


class test_arch_markup(TestCase):

    def test_wiring_and_unverified(self):
        out = arch_markup(snap())
        for token in ('CF Deployed Architecture', 'CloudFront', 'Firehose', 'UNVERIFIED',
                      'S3', 'cf-logs-bucket', 'E1ABC', 'sgraph.ai', 'CloudWatch Log Groups'):
            assert token in out, token

    def test_error_line_shown(self):
        s = snap()
        s.cf_error = 'Unable to locate credentials'
        out = arch_markup(s)
        assert 'Unable to locate credentials' in out


class test_arch_plain(TestCase):

    def test_no_markup(self):
        out = arch_plain(snap())
        assert 'CF Deployed Architecture' in out
        assert 'UNVERIFIED'               in out
        assert '['                        not in out
