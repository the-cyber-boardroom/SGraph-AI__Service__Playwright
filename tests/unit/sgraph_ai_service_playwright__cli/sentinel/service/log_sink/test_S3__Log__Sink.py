# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for S3__Log__Sink (via S3__AWS__Client__In_Memory; no AWS)
# Same key layout + round-trip as the local-FS sink.
# ═══════════════════════════════════════════════════════════════════════════════

from tests.unit.sgraph_ai_service_playwright__cli.aws.s3.service.S3__AWS__Client__In_Memory import S3__AWS__Client__In_Memory
from sgraph_ai_service_playwright__cli.sentinel.schemas.Schema__Sentinel__Log_Record         import Schema__Sentinel__Log_Record
from sgraph_ai_service_playwright__cli.sentinel.service.log_sink.S3__Log__Sink                import S3__Log__Sink

_BUCKET = 'sg-sentinel-logs-test'


def _sink() -> S3__Log__Sink:
    s3 = S3__AWS__Client__In_Memory().add_bucket(_BUCKET)
    return S3__Log__Sink(bucket=_BUCKET, s3_client=s3)


def _record(request_id='sn-1', received_at='2026-05-23T14:30:00Z', verdict='block') -> Schema__Sentinel__Log_Record:
    return Schema__Sentinel__Log_Record(request_id=request_id, received_at=received_at, method='GET',
                                        path='/etc/passwd', host='h', source_ip='abc', verdict=verdict,
                                        reason='path never valid', rule_id='0012')


class TestWriteRead:
    def test_write_uses_shared_key_layout(self):
        assert _sink().write(_record()) == 'sentinel/2026/05/23/14/sn-1.json'

    def test_round_trip(self):
        sink = _sink()
        sink.write(_record(request_id='sn-a'))
        sink.write(_record(request_id='sn-b'))
        records = sink.read_all()
        assert len(records) == 2
        assert str(records[0].rule_id) == '0012'

    def test_get_by_request_id(self):
        sink = _sink()
        sink.write(_record(request_id='sn-find'))
        assert str(sink.get('sn-find').request_id) == 'sn-find'
        assert sink.get('sn-missing') is None
