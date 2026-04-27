# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — SG_Send__File__Viewer
# Drives the real viewer with a recording S3 fetcher (canned bytes, no boto3).
# Asserts:
#   - raw_text gunzips and returns the TSV string verbatim
#   - parsed delegates to CF__Realtime__Log__Parser and returns (records, skipped)
#   - empty bytes → empty string / empty records
# ═══════════════════════════════════════════════════════════════════════════════

import gzip
from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.Bot__Classifier            import Bot__Classifier
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.CF__Realtime__Log__Parser import CF__Realtime__Log__Parser
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.S3__Object__Fetcher       import S3__Object__Fetcher
from sgraph_ai_service_playwright__cli.elastic.lets.cf.sg_send.service.SG_Send__File__Viewer    import SG_Send__File__Viewer


# ─── 26-column real-CF row (matches what production logs deliver) ────────────
SAMPLE_TSV_ROW = '\t'.join([
    '1777075217.167',                                                                # 0  timestamp
    '0.012',                                                                          # 1  time-taken
    '200',                                                                            # 2  sc-status
    '1234',                                                                           # 3  sc-bytes
    'GET',                                                                            # 4  cs-method
    'https',                                                                          # 5  cs-protocol
    'workspace.sgraph.ai',                                                            # 6  cs-host
    '/api/health',                                                                    # 7  cs-uri-stem
    'HIO52-P4',                                                                       # 8  x-edge-location
    'reqid-abc',                                                                      # 9  x-edge-request-id
    '0.005',                                                                          # 10 ttfb
    'HTTP/2.0',                                                                       # 11 protocol-version
    'Mozilla/5.0',                                                                    # 12 ua
    '-',                                                                              # 13 referer
    'Hit',                                                                            # 14 edge-result
    'TLSv1.3',                                                                        # 15 ssl-protocol
    'TLS_AES_128_GCM_SHA256',                                                         # 16 ssl-cipher
    'application/json',                                                               # 17 content-type
    '50',                                                                             # 18 content-len
    '-',                                                                              # 19 range-start
    '-',                                                                              # 20 range-end
    'GB',                                                                             # 21 country
    'gzip',                                                                           # 22 accept-encoding
    '-',                                                                              # 23 fle-status
    '0.001',                                                                          # 24 origin-fbl
    '0.011',                                                                          # 25 origin-lbl
])


class Recording__S3__Fetcher(S3__Object__Fetcher):                                   # Override the public method directly — no boto3 reach-through
    fetch_log : list                                                                  # [(bucket, key, region), ...]
    payload   : bytes

    def get_object_bytes(self, bucket, key, region=''):
        self.fetch_log.append((bucket, key, region))
        self.counter.s3()                                                             # Mirror real fetcher's behaviour so total() reflects calls
        return self.payload


def make_viewer(payload: bytes) -> SG_Send__File__Viewer:
    return SG_Send__File__Viewer(s3_fetcher = Recording__S3__Fetcher(fetch_log=[], payload=payload),
                                  parser     = CF__Realtime__Log__Parser(bot_classifier=Bot__Classifier()))


class test_raw_text(TestCase):

    def test_gunzips_and_returns_tsv_string(self):
        tsv     = SAMPLE_TSV_ROW + '\n' + SAMPLE_TSV_ROW + '\n'
        gz      = gzip.compress(tsv.encode('utf-8'))
        viewer  = make_viewer(gz)
        result  = viewer.raw_text(bucket='b', key='cloudfront-realtime/2026/04/25/14/file.gz', region='eu-west-2')
        assert result == tsv
        assert viewer.s3_fetcher.fetch_log == [('b', 'cloudfront-realtime/2026/04/25/14/file.gz', 'eu-west-2')]

    def test_empty_bytes_returns_empty_string(self):                                 # Empty .gz / 0-byte object
        viewer = make_viewer(b'')
        assert viewer.raw_text(bucket='b', key='k') == ''


class test_parsed(TestCase):

    def test_returns_records_and_skipped_count(self):
        tsv     = SAMPLE_TSV_ROW + '\n' + SAMPLE_TSV_ROW + '\n'
        gz      = gzip.compress(tsv.encode('utf-8'))
        viewer  = make_viewer(gz)
        records, skipped = viewer.parsed(bucket='b', key='k')
        assert len(records) == 2
        assert skipped == 0
        assert int(records[0].sc_status) == 200
        assert str(records[0].cs_host)   == 'workspace.sgraph.ai'

    def test_garbage_lines_counted_as_skipped(self):                                 # Wrong column count → row skipped, not parsed
        bad_row = 'one\ttwo\tthree'
        tsv     = SAMPLE_TSV_ROW + '\n' + bad_row + '\n'
        gz      = gzip.compress(tsv.encode('utf-8'))
        viewer  = make_viewer(gz)
        records, skipped = viewer.parsed(bucket='b', key='k')
        assert len(records) == 1
        assert skipped == 1

    def test_empty_bytes_returns_empty_records_zero_skipped(self):
        viewer = make_viewer(b'')
        records, skipped = viewer.parsed(bucket='b', key='k')
        assert len(records) == 0
        assert skipped == 0
