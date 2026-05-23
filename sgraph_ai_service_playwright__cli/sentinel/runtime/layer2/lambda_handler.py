# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — lambda_handler (Lambda@Edge origin-request adapter, AWS only)
# Reads the x-sentinel-signal header L1 set, runs the SAME L2 actor, and either
# returns a CloudFront response (block) or the request (forward to origin). L2 is
# the sole actor + sole I/O owner; it writes the log record to S3.
#
# Lambda@Edge has no environment variables — config (log bucket, region) is
# templated into _sentinel_config.py in the deployment zip by Sentinel__Deployer.
# handle_request() is the testable core (inject any actor); handler() wires the
# real S3-backed actor. The _sentinel_config import is lazy so unit tests that
# call handle_request() never need the generated file.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.sentinel.enums.Enum__Sentinel__Target import Enum__Sentinel__Target
from sgraph_ai_service_playwright__cli.sentinel.service.Signal__Codec        import Signal__Codec

_SIGNAL_HEADER = 'x-sentinel-signal'


def _header_value(request: dict, name: str) -> str:
    items = (request.get('headers') or {}).get(name, []) or []
    return items[0].get('value', '') if items else ''


def _block_response(http_status: int, body: str = '') -> dict:                       # CloudFront response object
    status_text = {403: 'Forbidden', 404: 'Not Found'}.get(http_status, 'Blocked')
    return {'status'           : str(http_status),
            'statusDescription': status_text,
            'headers'          : {'content-type': [{'key': 'Content-Type', 'value': 'text/plain'}]},
            'body'             : body}


def handle_request(request: dict, actor) -> dict:                                    # testable core — returns request (pass) or a response (block)
    raw = _header_value(request, _SIGNAL_HEADER)
    if not raw:
        return request                                                               # no signal (L1 always sets it) → fail-open to origin
    signal      = Signal__Codec().decode(raw)
    enforcement = actor.handle(signal, Enum__Sentinel__Target.AWS)                   # L2 enforces + writes the log record
    if enforcement.pass_to_origin:
        return request
    return _block_response(enforcement.http_status, str(enforcement.body))


def build_actor():                                                                   # real S3-backed actor (live only)
    from sgraph_ai_service_playwright__cli.aws.s3.primitives.Safe_Str__S3__Bucket    import Safe_Str__S3__Bucket
    from sgraph_ai_service_playwright__cli.aws.s3.service.S3__AWS__Client            import S3__AWS__Client
    from sgraph_ai_service_playwright__cli.sentinel.runtime.layer2.Sentinel__L2__Actor import Sentinel__L2__Actor
    from sgraph_ai_service_playwright__cli.sentinel.service.log_sink.S3__Log__Sink   import S3__Log__Sink
    import _sentinel_config as cfg                                                   # generated into the zip by the deployer

    sink = S3__Log__Sink(bucket=Safe_Str__S3__Bucket(cfg.LOG_BUCKET), s3_client=S3__AWS__Client(region=cfg.REGION))
    return Sentinel__L2__Actor(log_sink=sink)


def handler(event, context=None):                                                    # Lambda@Edge entry (origin-request)
    request = event['Records'][0]['cf']['request']
    return handle_request(request, build_actor())
