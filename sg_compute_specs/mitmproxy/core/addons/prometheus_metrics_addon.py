# ═══════════════════════════════════════════════════════════════════════════════
# Agent Mitmproxy — Prometheus Metrics Addon
#
# Duck-typed mitmproxy addon (no mitmproxy imports at module load time).
# Maintains in-memory Prometheus Counters and Histograms in a dedicated
# CollectorRegistry (MITMPROXY_REGISTRY). Updated on each completed flow via
# response(). Routes__Metrics calls generate_latest(MITMPROXY_REGISTRY) to
# serialise for GET /metrics.
# ═══════════════════════════════════════════════════════════════════════════════

from prometheus_client import CollectorRegistry, Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

MITMPROXY_REGISTRY = CollectorRegistry()

_FLOWS_TOTAL = Counter(
    'sg_mitmproxy_flows_total',
    'Total proxy flows by scheme and HTTP-class status',
    ['scheme', 'status_class'],
    registry = MITMPROXY_REGISTRY,
)

_FLOW_DURATION_SECONDS = Histogram(
    'sg_mitmproxy_flow_duration_seconds',
    'Flow round-trip duration in seconds',
    ['scheme'],
    buckets  = [.05, .1, .25, .5, 1, 2.5, 5, 10, 30, 60],
    registry = MITMPROXY_REGISTRY,
)

_BYTES_REQUEST_TOTAL = Counter(
    'sg_mitmproxy_bytes_request_total',
    'Total request body bytes proxied',
    registry = MITMPROXY_REGISTRY,
)

_BYTES_RESPONSE_TOTAL = Counter(
    'sg_mitmproxy_bytes_response_total',
    'Total response body bytes proxied',
    registry = MITMPROXY_REGISTRY,
)


def _status_class(code) -> str:                                                     # bucket raw status code into 2xx/3xx/4xx/5xx/unknown
    if code is None:
        return 'unknown'
    c = int(code)
    if 200 <= c < 300: return '2xx'
    if 300 <= c < 400: return '3xx'
    if 400 <= c < 500: return '4xx'
    if 500 <= c < 600: return '5xx'
    return 'other'


class Prometheus_Metrics:

    def response(self, flow):
        request  = flow.request
        response = flow.response
        scheme   = getattr(request,  'scheme',       'unknown') or 'unknown'
        status   = getattr(response, 'status_code',  None)
        start_ts = getattr(request,  'timestamp_start', None)
        end_ts   = (getattr(response, 'timestamp_end',   None)
                    or getattr(response, 'timestamp_start', None))

        _FLOWS_TOTAL.labels(scheme=scheme, status_class=_status_class(status)).inc()

        if start_ts and end_ts and end_ts > start_ts:
            _FLOW_DURATION_SECONDS.labels(scheme=scheme).observe(end_ts - start_ts)

        _BYTES_REQUEST_TOTAL .inc(len(getattr(request,  'content', b'') or b''))
        _BYTES_RESPONSE_TOTAL.inc(len(getattr(response, 'content', b'') or b''))


addons = [Prometheus_Metrics()]
