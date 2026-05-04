# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Vnc__Interceptor__Resolver
# Pure logic for N5 interceptor selection. Turns a Schema__Vnc__Interceptor__Choice
# into the two artefacts the user-data needs to bake:
#   - the Python source to write at /opt/interceptors/runtime/active.py
#     (always — even kind=NONE writes a no-op so mitmproxy's --scripts arg
#      stays static across boots)
#   - a label suitable for the response / tag
#
# Three shapes:
#   kind=NONE                 → no-op source ('# sg-vnc: no interceptor\n')
#                                + label='' (tag will be 'none')
#   kind=NAME   + name='ex'   → uses Vnc__Examples__Library to read
#                                examples/<name>.py source
#                                + label='ex'
#   kind=INLINE + inline_src  → embeds the operator's source verbatim
#                                + label='inline'
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.vnc.enums.Enum__Vnc__Interceptor__Kind       import Enum__Vnc__Interceptor__Kind
from sgraph_ai_service_playwright__cli.vnc.schemas.Schema__Vnc__Interceptor__Choice import Schema__Vnc__Interceptor__Choice


NO_OP_SOURCE = "# sg-vnc: no interceptor active\n"                                  # mitmproxy is happy with an empty addons module


# Baked example sources (kept inline for now — keeps the AMI 100% self-
# contained per doc 1 decision #8). Examples are tiny by design; a future
# slice can split them into a vnc/mitmproxy/interceptors/examples/ tree on
# disk and have user-data copy them in.
EXAMPLE_HEADER_LOGGER = """\
from mitmproxy import http


def request(flow: http.HTTPFlow) -> None:
    print(f'[sg-vnc:header_logger] {flow.request.method} {flow.request.pretty_url}')
    for header, value in flow.request.headers.items():
        print(f'  {header}: {value}')
"""


EXAMPLE_HEADER_INJECTOR = """\
from mitmproxy import http


def request(flow: http.HTTPFlow) -> None:
    flow.request.headers['X-Sg-Vnc-Marker'] = 'header_injector'
"""


EXAMPLE_FLOW_RECORDER = """\
from mitmproxy import http


def response(flow: http.HTTPFlow) -> None:
    print(f'[sg-vnc:flow_recorder] {flow.request.method} {flow.request.pretty_url} '
          f'-> {flow.response.status_code if flow.response else "?"}')
"""


EXAMPLES = {                                                                        # Locked by test
    'header_logger'  : EXAMPLE_HEADER_LOGGER  ,
    'header_injector': EXAMPLE_HEADER_INJECTOR,
    'flow_recorder'  : EXAMPLE_FLOW_RECORDER  ,
}


def list_examples() -> list:                                                        # For `sp vnc interceptors` typer command
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
