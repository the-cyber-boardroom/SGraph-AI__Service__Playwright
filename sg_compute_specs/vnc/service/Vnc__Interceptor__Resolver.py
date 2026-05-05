# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — VNC: Vnc__Interceptor__Resolver
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute_specs.vnc.enums.Enum__Vnc__Interceptor__Kind                        import Enum__Vnc__Interceptor__Kind
from sg_compute_specs.vnc.schemas.Schema__Vnc__Interceptor__Choice                  import Schema__Vnc__Interceptor__Choice


NO_OP_SOURCE = "# sg-vnc: no interceptor active\n"


EXAMPLE_HEADER_LOGGER = '''\
from mitmproxy import http


def request(flow: http.HTTPFlow) -> None:
    print(f'[sg-vnc:header_logger] {flow.request.method} {flow.request.pretty_url}')
    for header, value in flow.request.headers.items():
        print(f'  {header}: {value}')
'''


EXAMPLE_HEADER_INJECTOR = '''\
from mitmproxy import http


def request(flow: http.HTTPFlow) -> None:
    flow.request.headers['X-Sg-Vnc-Marker'] = 'header_injector'
'''


EXAMPLE_FLOW_RECORDER = '''\
from mitmproxy import http


def response(flow: http.HTTPFlow) -> None:
    print(f'[sg-vnc:flow_recorder] {flow.request.method} {flow.request.pretty_url} '
          f'-> {flow.response.status_code if flow.response else "?"}')
'''


EXAMPLES = {                                                                        # Locked by test
    'header_logger'  : EXAMPLE_HEADER_LOGGER  ,
    'header_injector': EXAMPLE_HEADER_INJECTOR,
    'flow_recorder'  : EXAMPLE_FLOW_RECORDER  ,
}


def list_examples() -> list:
    return sorted(EXAMPLES.keys())


class Vnc__Interceptor__Resolver(Type_Safe):

    def resolve(self, choice: Schema__Vnc__Interceptor__Choice = None) -> tuple:    # → (source: str, label: str)
        choice = choice or Schema__Vnc__Interceptor__Choice()

        if choice.kind == Enum__Vnc__Interceptor__Kind.NAME:
            name = str(choice.name)
            if name not in EXAMPLES:
                raise ValueError(f'unknown interceptor example: {name!r}; '
                                 f'available: {", ".join(list_examples())}')
            return EXAMPLES[name], name

        if choice.kind == Enum__Vnc__Interceptor__Kind.INLINE:
            source = str(choice.inline_source)
            if not source:
                raise ValueError('inline interceptor requires non-empty inline_source')
            return source, 'inline'

        return NO_OP_SOURCE, ''                                                     # NONE
