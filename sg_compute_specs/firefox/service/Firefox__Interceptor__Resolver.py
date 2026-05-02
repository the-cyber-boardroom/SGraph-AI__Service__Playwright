# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Firefox: Firefox__Interceptor__Resolver
# Turns a Schema__Firefox__Interceptor__Choice into (source: str, label: str).
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute_specs.firefox.enums.Enum__Firefox__Interceptor__Kind                import Enum__Firefox__Interceptor__Kind
from sg_compute_specs.firefox.schemas.Schema__Firefox__Interceptor__Choice          import Schema__Firefox__Interceptor__Choice


NO_OP_SOURCE = "# sg-firefox: no interceptor active\n"


EXAMPLE_HEADER_LOGGER = """\
from mitmproxy import http


def request(flow: http.HTTPFlow) -> None:
    print(f'[sg-firefox:header_logger] {flow.request.method} {flow.request.pretty_url}')
    for header, value in flow.request.headers.items():
        print(f'  {header}: {value}')
"""


EXAMPLE_HEADER_INJECTOR = """\
from mitmproxy import http


def request(flow: http.HTTPFlow) -> None:
    flow.request.headers['X-Sg-Firefox-Marker'] = 'header_injector'
"""


EXAMPLE_FLOW_RECORDER = """\
from mitmproxy import http


def response(flow: http.HTTPFlow) -> None:
    print(f'[sg-firefox:flow_recorder] {flow.request.method} {flow.request.pretty_url} '
          f'-> {flow.response.status_code if flow.response else "?"}')
"""


EXAMPLE_RESPONSE_LOGGER = """\
from mitmproxy import http


def response(flow: http.HTTPFlow) -> None:
    status = flow.response.status_code if flow.response else '?'
    ct     = (flow.response.headers.get('content-type', '') if flow.response else '').split(';')[0]
    print(f'[sg-firefox:response_logger] {status} {flow.request.method} {flow.request.pretty_url}  [{ct}]')
"""


EXAMPLE_COOKIE_LOGGER = """\
from mitmproxy import http


def response(flow: http.HTTPFlow) -> None:
    if not flow.response:
        return
    for header, value in flow.response.headers.items(multi=True):
        if header.lower() == 'set-cookie':
            name = value.split('=', 1)[0]
            print(f'[sg-firefox:cookie_logger] SET {name!r}  <- {flow.request.pretty_url}')
"""


EXAMPLE_BLOCK_TRACKERS = """\
from mitmproxy import http

BLOCKED = {
    'doubleclick.net', 'googlesyndication.com', 'googletagmanager.com',
    'google-analytics.com', 'facebook.net', 'connect.facebook.net',
    'hotjar.com', 'scorecardresearch.com', 'outbrain.com', 'taboola.com',
}


def request(flow: http.HTTPFlow) -> None:
    host = flow.request.host.lower()
    if any(host == d or host.endswith('.' + d) for d in BLOCKED):
        print(f'[sg-firefox:block_trackers] blocked {host}')
        flow.response = http.Response.make(204)
"""


EXAMPLE_REQUEST_TIMER = """\
import time
from mitmproxy import http


def request(flow: http.HTTPFlow) -> None:
    flow.request.timestamp_start_custom = time.monotonic()


def response(flow: http.HTTPFlow) -> None:
    start = getattr(flow.request, 'timestamp_start_custom', None)
    if start is None:
        return
    elapsed_ms = int((time.monotonic() - start) * 1000)
    status     = flow.response.status_code if flow.response else '?'
    print(f'[sg-firefox:request_timer] {elapsed_ms:>6}ms  {status}  {flow.request.pretty_url}')
"""


EXAMPLE_ADD_CORS = """\
from mitmproxy import http


def response(flow: http.HTTPFlow) -> None:
    if flow.response:
        flow.response.headers['Access-Control-Allow-Origin']  = '*'
        flow.response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        flow.response.headers['Access-Control-Allow-Headers'] = '*'
"""


EXAMPLES = {
    'header_logger'  : EXAMPLE_HEADER_LOGGER  ,
    'header_injector': EXAMPLE_HEADER_INJECTOR,
    'flow_recorder'  : EXAMPLE_FLOW_RECORDER  ,
    'response_logger': EXAMPLE_RESPONSE_LOGGER ,
    'cookie_logger'  : EXAMPLE_COOKIE_LOGGER   ,
    'block_trackers' : EXAMPLE_BLOCK_TRACKERS  ,
    'request_timer'  : EXAMPLE_REQUEST_TIMER   ,
    'add_cors'       : EXAMPLE_ADD_CORS        ,
}


def list_examples() -> list:
    return sorted(EXAMPLES.keys())


class Firefox__Interceptor__Resolver(Type_Safe):

    def resolve(self, choice: Schema__Firefox__Interceptor__Choice = None) -> tuple:
        choice = choice or Schema__Firefox__Interceptor__Choice()

        if choice.kind == Enum__Firefox__Interceptor__Kind.NAME:
            name = str(choice.name)
            if name not in EXAMPLES:
                raise ValueError(f'unknown interceptor example: {name!r}; '
                                 f'available: {", ".join(list_examples())}')
            return EXAMPLES[name], name

        if choice.kind == Enum__Firefox__Interceptor__Kind.INLINE:
            source = str(choice.inline_source)
            if not source:
                raise ValueError('inline interceptor requires non-empty inline_source')
            return source, 'inline'

        return NO_OP_SOURCE, ''
