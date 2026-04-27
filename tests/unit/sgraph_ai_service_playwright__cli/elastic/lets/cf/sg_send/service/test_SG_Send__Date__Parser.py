# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — SG_Send__Date__Parser
# Pin the accepted formats and the friendly errors.  Year defaults to 2026
# (per the user's call: "we can assume this is 2026" — sg-send is the only
# place this default lives; refactor when we go multi-year).
# ═══════════════════════════════════════════════════════════════════════════════

import pytest
from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.sg_send.service.SG_Send__Date__Parser import (
    parse_sg_send_date, s3_prefix_for_date, render_date_label, DEFAULT_YEAR)


class test_parse_sg_send_date(TestCase):

    def test_mm_dd_assumes_default_year(self):
        assert parse_sg_send_date('04/25')   == (DEFAULT_YEAR, 4, 25, None)

    def test_mm_dd_hh_assumes_default_year(self):
        assert parse_sg_send_date('04/25/14') == (DEFAULT_YEAR, 4, 25, 14)

    def test_yyyy_mm_dd_uses_explicit_year(self):
        assert parse_sg_send_date('2026/04/25') == (2026, 4, 25, None)

    def test_yyyy_mm_dd_hh_uses_explicit_year(self):
        assert parse_sg_send_date('2026/04/25/14') == (2026, 4, 25, 14)

    def test_hyphen_separators_work(self):                                           # ISO-style hyphens map onto the same parser
        assert parse_sg_send_date('2026-04-25') == (2026, 4, 25, None)

    def test_leading_or_trailing_slashes_tolerated(self):
        assert parse_sg_send_date('/04/25/')  == (DEFAULT_YEAR, 4, 25, None)

    def test_blank_raises(self):
        with pytest.raises(ValueError, match='date is required'):
            parse_sg_send_date('')

    def test_too_many_segments_raises(self):
        with pytest.raises(ValueError, match='expected'):
            parse_sg_send_date('2026/04/25/14/15')

    def test_non_integer_segment_raises(self):
        with pytest.raises(ValueError, match='integers'):
            parse_sg_send_date('2026/abc/25')

    def test_year_out_of_range_raises(self):
        with pytest.raises(ValueError, match='year .* out of range'):
            parse_sg_send_date('1999/04/25')

    def test_month_out_of_range_raises(self):
        with pytest.raises(ValueError, match='month .* out of range'):
            parse_sg_send_date('13/25')

    def test_day_out_of_range_raises(self):
        with pytest.raises(ValueError, match='day .* out of range'):
            parse_sg_send_date('04/32')

    def test_hour_out_of_range_raises(self):
        with pytest.raises(ValueError, match='hour .* out of range'):
            parse_sg_send_date('04/25/24')


class test_s3_prefix_for_date(TestCase):

    def test_day_prefix_has_trailing_slash(self):                                    # `prefix=` requires a trailing slash for S3 list-objects to scope to a directory
        assert s3_prefix_for_date(2026, 4, 25) == 'cloudfront-realtime/2026/04/25/'

    def test_hour_prefix_has_no_trailing_slash(self):                                # Hour-level prefix still scopes via list-objects (CF logs are placed under HH/ folders)
        assert s3_prefix_for_date(2026, 4, 25, 14) == 'cloudfront-realtime/2026/04/25/14'

    def test_zero_pads_single_digits(self):
        assert s3_prefix_for_date(2026, 1, 5, 3) == 'cloudfront-realtime/2026/01/05/03'


class test_render_date_label(TestCase):

    def test_day_only(self):
        assert render_date_label(2026, 4, 25)     == '2026-04-25'

    def test_with_hour(self):
        assert render_date_label(2026, 4, 25, 14) == '2026-04-25 hour 14:00'
