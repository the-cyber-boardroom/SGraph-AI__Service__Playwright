# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — CF__Realtime__Log__Parser
# Pins the TSV → Schema__CF__Event__Record orchestrator using the user's two
# real CF log lines as golden samples (preserved verbatim).
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.enums.Enum__CF__Bot__Category       import Enum__CF__Bot__Category
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.enums.Enum__CF__Edge__Result__Type  import Enum__CF__Edge__Result__Type
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.enums.Enum__CF__Method              import Enum__CF__Method
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.enums.Enum__CF__Protocol            import Enum__CF__Protocol
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.enums.Enum__CF__SSL__Protocol       import Enum__CF__SSL__Protocol
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.enums.Enum__CF__Status__Class       import Enum__CF__Status__Class
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.Bot__Classifier      import Bot__Classifier
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.CF__Realtime__Log__Parser import CF__Realtime__Log__Parser


# ─── Golden samples — verbatim from the user's pasted CF log lines ───────────
# Line 1: wpbot hits /enhancecp, gets 302 from a CloudFront Function
LINE_1 = '1777075217.167\t0.001\t302\t246\tGET\thttps\tsgraph.ai\t/enhancecp\tHIO52-P4\t2TZI-f7L0PmDR-76lAEx4wdq-StamTTbisIdbMSYhB4eVeyTcPy0qw==\t0.001\tHTTP/2.0\tMozilla/5.0%20(compatible;%20wpbot/1.4;%20+https://forms.gle/ajBaxygz9jSR8p8G9)\t-\tFunctionGeneratedResponse\tTLSv1.3\tTLS_AES_128_GCM_SHA256\t-\t0\t-\t-\tUS\tgzip\t-\t-\t-'

# Line 2: same wpbot hits /robots.txt, gets 403 (Error result type) with origin call
LINE_2 = '1777075217.160\t0.924\t403\t363\tGET\thttps\tsgraph.ai\t/robots.txt\tHIO52-P4\tBMtxwcXadQXVuawbKov5bSBaxNrAxnxuEI-8RU1AH4i5hUSarxBZwA==\t0.924\tHTTP/2.0\tMozilla/5.0%20(compatible;%20wpbot/1.4;%20+https://forms.gle/ajBaxygz9jSR8p8G9)\t-\tError\tTLSv1.3\tTLS_AES_128_GCM_SHA256\tapplication/xml\t-\t-\t-\tUS\tgzip\t-\t0.424\t0.424'


def make_parser() -> CF__Realtime__Log__Parser:
    return CF__Realtime__Log__Parser(bot_classifier=Bot__Classifier())


class test_CF__Realtime__Log__Parser__line_1(TestCase):                             # /enhancecp 302 (FunctionGeneratedResponse, no origin call)

    def test_parses_to_one_record(self):
        records, skipped = make_parser().parse(LINE_1)
        assert len(records) == 1
        assert skipped == 0

    def test_status_and_class(self):
        records, _ = make_parser().parse(LINE_1)
        r = records[0]
        assert r.sc_status        == 302
        assert r.sc_status_class  == Enum__CF__Status__Class.REDIRECTION

    def test_method_protocol_host_uri(self):
        r = make_parser().parse(LINE_1)[0][0]
        assert r.cs_method   == Enum__CF__Method.GET
        assert r.cs_protocol == Enum__CF__Protocol.HTTPS
        assert str(r.cs_host)     == 'sgraph.ai'
        assert str(r.cs_uri_stem) == '/enhancecp'

    def test_edge_location_and_request_id(self):
        r = make_parser().parse(LINE_1)[0][0]
        assert str(r.x_edge_location)   == 'HIO52-P4'
        assert str(r.x_edge_request_id) == '2TZI-f7L0PmDR-76lAEx4wdq-StamTTbisIdbMSYhB4eVeyTcPy0qw=='

    def test_timing_in_ms(self):
        r = make_parser().parse(LINE_1)[0][0]
        assert r.time_taken_ms == 1                                                  # 0.001s × 1000
        assert r.ttfb_ms       == 1
        assert r.origin_fbl_ms == -1                                                 # "-" (no origin call)
        assert r.origin_lbl_ms == -1

    def test_user_agent_url_decoded(self):                                          # %20 → space, %2F → /, etc.
        r = make_parser().parse(LINE_1)[0][0]
        assert 'wpbot/1.4' in str(r.cs_user_agent)
        assert '%20'       not in str(r.cs_user_agent)                              # No URL-encoded chars survive

    def test_referer_empty_from_dash(self):
        r = make_parser().parse(LINE_1)[0][0]
        assert str(r.cs_referer) == ''

    def test_edge_result_type_function_generated(self):
        r = make_parser().parse(LINE_1)[0][0]
        assert r.x_edge_result_type == Enum__CF__Edge__Result__Type.FunctionGeneratedResponse
        assert r.cache_hit          is False                                         # Function-generated is NOT a cache hit

    def test_ssl(self):
        r = make_parser().parse(LINE_1)[0][0]
        assert r.ssl_protocol      == Enum__CF__SSL__Protocol.TLSv1_3
        assert str(r.ssl_cipher)   == 'TLS_AES_128_GCM_SHA256'

    def test_country_and_encoding(self):
        r = make_parser().parse(LINE_1)[0][0]
        assert str(r.c_country)          == 'US'
        assert str(r.cs_accept_encoding) == 'gzip'

    def test_bot_detected(self):                                                    # wpbot is in KNOWN_BOT_PATTERNS
        r = make_parser().parse(LINE_1)[0][0]
        assert r.bot_category == Enum__CF__Bot__Category.BOT_KNOWN
        assert r.is_bot       is True

    def test_timestamp_iso_with_millis(self):
        r = make_parser().parse(LINE_1)[0][0]
        assert str(r.timestamp) == '2026-04-25T00:00:17.167Z'


class test_CF__Realtime__Log__Parser__line_2(TestCase):                             # /robots.txt 403 (Error, with origin call)

    def test_status_and_class(self):
        r = make_parser().parse(LINE_2)[0][0]
        assert r.sc_status       == 403
        assert r.sc_status_class == Enum__CF__Status__Class.CLIENT_ERROR

    def test_uri_robots_txt(self):
        r = make_parser().parse(LINE_2)[0][0]
        assert str(r.cs_uri_stem) == '/robots.txt'

    def test_edge_result_type_error(self):
        r = make_parser().parse(LINE_2)[0][0]
        assert r.x_edge_result_type == Enum__CF__Edge__Result__Type.Error
        assert r.cache_hit          is False

    def test_origin_latency_populated(self):                                        # Origin first/last byte latency = 0.424s × 1000 = 424 ms
        r = make_parser().parse(LINE_2)[0][0]
        assert r.origin_fbl_ms == 424
        assert r.origin_lbl_ms == 424

    def test_content_type_present(self):
        r = make_parser().parse(LINE_2)[0][0]
        assert str(r.sc_content_type) == 'application/xml'

    def test_time_taken_924ms(self):
        r = make_parser().parse(LINE_2)[0][0]
        assert r.time_taken_ms == 924                                                # 0.924s × 1000

    def test_bot_category_still_known(self):
        r = make_parser().parse(LINE_2)[0][0]
        assert r.bot_category == Enum__CF__Bot__Category.BOT_KNOWN


class test_CF__Realtime__Log__Parser__multiline(TestCase):                          # Real .gz files contain many lines

    def test_two_lines_two_records_with_line_indices(self):
        records, skipped = make_parser().parse(LINE_1 + '\n' + LINE_2)
        assert len(records) == 2
        assert skipped == 0
        assert records[0].line_index == 0
        assert records[1].line_index == 1

    def test_trailing_newline_does_not_count(self):
        records, skipped = make_parser().parse(LINE_1 + '\n')
        assert len(records) == 1
        assert skipped == 0

    def test_blank_lines_skipped_silently(self):                                    # Empty lines are NOT counted as skipped (they're not failures)
        records, skipped = make_parser().parse(LINE_1 + '\n\n\n' + LINE_2)
        assert len(records) == 2
        assert skipped == 0


class test_CF__Realtime__Log__Parser__edge_cases(TestCase):

    def test_empty_input(self):
        records, skipped = make_parser().parse('')
        assert len(records) == 0
        assert skipped == 0

    def test_wrong_column_count_skipped(self):
        broken = '1777075217.167\t0.001\t302'                                        # Only 3 columns, expected 26
        records, skipped = make_parser().parse(broken)
        assert len(records) == 0
        assert skipped == 1

    def test_one_good_one_bad(self):
        records, skipped = make_parser().parse(LINE_1 + '\nshort\tline\twrong')
        assert len(records) == 1
        assert skipped == 1

    def test_unknown_enum_value_falls_back_to_default(self):                        # safe_enum maps unrecognised wire values to the default
        weird = LINE_1.replace('FunctionGeneratedResponse', 'SomeNewResultTypeAWSAdded')
        r = make_parser().parse(weird)[0][0]
        assert r.x_edge_result_type == Enum__CF__Edge__Result__Type.Other
