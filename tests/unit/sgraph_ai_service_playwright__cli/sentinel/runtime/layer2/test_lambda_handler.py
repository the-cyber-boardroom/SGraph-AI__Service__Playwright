# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for the Lambda@Edge handler core (handle_request)
# No AWS: an InMemory-sink actor is injected; a synthetic CloudFront request carries
# the x-sentinel-signal header. Asserts block → CF response, allow → forward request.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.sentinel.enums.Enum__Sentinel__Action          import Enum__Sentinel__Action
from sgraph_ai_service_playwright__cli.sentinel.enums.Enum__Sentinel__Verdict         import Enum__Sentinel__Verdict
from sgraph_ai_service_playwright__cli.sentinel.runtime.layer2.Sentinel__L2__Actor    import Sentinel__L2__Actor
from sgraph_ai_service_playwright__cli.sentinel.runtime.layer2.lambda_handler         import handle_request
from sgraph_ai_service_playwright__cli.sentinel.schemas.Schema__Sentinel__Captured    import Schema__Sentinel__Captured
from sgraph_ai_service_playwright__cli.sentinel.schemas.Schema__Sentinel__Signal      import Schema__Sentinel__Signal
from sgraph_ai_service_playwright__cli.sentinel.service.Signal__Codec                 import Signal__Codec
from sgraph_ai_service_playwright__cli.sentinel.service.log_sink.InMemory__Log__Sink  import InMemory__Log__Sink


def _request_with_signal(verdict, action, rule_id='0012'):
    captured = Schema__Sentinel__Captured(method='GET', path='/etc/passwd', host='h',
                                          source_ip='1.2.3.4', received_at='2026-05-23T10:00:00Z', cache_status='miss')
    signal   = Schema__Sentinel__Signal(request_id='sn-1', captured=captured, verdict=verdict,
                                        reason='path never valid', rule_id=rule_id, action=action)
    raw      = Signal__Codec().encode(signal)
    return {'headers': {'x-sentinel-signal': [{'key': 'x-sentinel-signal', 'value': raw}]},
            'uri': '/etc/passwd', 'method': 'GET'}


def _actor() -> Sentinel__L2__Actor:
    return Sentinel__L2__Actor(log_sink=InMemory__Log__Sink())


class TestBlock:
    def test_drop_403_returns_cf_response(self):
        actor  = _actor()
        result = handle_request(_request_with_signal(Enum__Sentinel__Verdict.BLOCK, Enum__Sentinel__Action.DROP_403), actor)
        assert result['status'] == '403'
        assert len(actor.log_sink.read_all()) == 1                                   # L2 wrote the record

    def test_deflect_404_returns_cf_response(self):
        result = handle_request(_request_with_signal(Enum__Sentinel__Verdict.BLOCK, Enum__Sentinel__Action.DEFLECT_404), _actor())
        assert result['status'] == '404'


class TestAllow:
    def test_allow_returns_the_request(self):
        request = _request_with_signal(Enum__Sentinel__Verdict.ALLOW, Enum__Sentinel__Action.PASS, rule_id='0001')
        result  = handle_request(request, _actor())
        assert result is request                                                     # forwarded to origin unchanged


class TestNoSignal:
    def test_missing_signal_fails_open_to_origin(self):
        request = {'headers': {}, 'uri': '/x'}
        assert handle_request(request, _actor()) is request
