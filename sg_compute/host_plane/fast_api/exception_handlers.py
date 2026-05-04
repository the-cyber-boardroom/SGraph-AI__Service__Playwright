# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — FastAPI exception handlers
# Bridges osbot-fast-api's Type_Safe request converter (which raises plain
# Python ValueError when a Safe_* primitive rejects user input) onto a proper
# HTTP 422 response with a structured body.
#
# Default FastAPI behaviour: uncaught ValueError → 500 Internal Server Error.
# That collapses every validation failure into a server fault, which:
#   • masks genuine 5xx from 4xx in metrics,
#   • gives callers no machine-readable clue which field was bad,
#   • makes API-GW / Function URL integrations noisy (false alarms).
#
# Message parsing
# ───────────────
# Safe_Str__* raises with messages like:
#   "in Safe_Str__Deploy_Name, value does not match required pattern: ^[...]$"
#   "in Safe_Str__Stack__Name, value cannot be None when allow_empty is False"
#   "in Safe_Int__Foo, value N is above max_value M"
#
# We extract the primitive class name (the "in <ClassName>," prefix) when
# present; if the message uses a different shape we surface it verbatim so
# callers at least see the useful text instead of an empty 500.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from fastapi                                                                        import FastAPI, Request
from fastapi.responses                                                              import JSONResponse


PRIMITIVE_CLASS_PATTERN = re.compile(r'^in (Safe_[A-Za-z0-9_]+|Enum_[A-Za-z0-9_]+),\s*(.+)$', re.DOTALL)
DETAIL_HINT             = 'Type-safe primitive rejected the request body. Review the `primitive` field in each entry of `detail` to see which type the value could not satisfy.'


def extract_primitive_and_message(raw: str) -> tuple:
    match = PRIMITIVE_CLASS_PATTERN.match(raw or '')
    if match:
        return match.group(1), match.group(2).strip()
    return '', (raw or '').strip()


def register_type_safe_handlers(app: FastAPI) -> None:                              # Call on setup() after super().setup()

    @app.exception_handler(ValueError)
    async def handle_value_error(request: Request, exc: ValueError):                # Framework-level bridge — do NOT add route-level try/excepts for the same errors
        primitive, message = extract_primitive_and_message(str(exc))
        return JSONResponse(status_code = 422,
                            content     = {'detail' : [{'type'      : 'type_safe_value_error',
                                                         'primitive': primitive               ,
                                                         'msg'      : message                 }],
                                           'hint'   : DETAIL_HINT                               })
