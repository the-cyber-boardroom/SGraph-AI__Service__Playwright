# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Echo__Payload
# Pure request→echo logic for the `httpget` echo server. Given the fields of an
# incoming request it builds the JSON echo body and an HTML rendering. No sockets,
# no framework — so it is identical across local / docker / Lambda / EC2 and fully
# unit-testable. The echo is what an origin behind SG/Sentinel saw, i.e. exactly the
# traffic that was NOT blocked at the edge.
# ═══════════════════════════════════════════════════════════════════════════════

import html


def echo_payload(method: str, path: str, querystring: str, headers: dict,
                 source_ip: str, body: str = '', seq: int = 0) -> dict:
    return {'echo'       : 'sg-sentinel-httpget',
            'seq'        : seq,
            'method'     : method,
            'path'       : path,
            'querystring': querystring,
            'source_ip'  : source_ip,
            'headers'    : {str(k).lower(): str(v) for k, v in (headers or {}).items()},
            'body'       : body or ''}


def render_html(payload: dict) -> str:
    rows = [f'<tr><td>{html.escape(str(k))}</td><td>{html.escape(str(v))}</td></tr>'
            for k, v in payload.items() if k != 'headers']
    header_rows = [f'<tr><td>{html.escape(k)}</td><td>{html.escape(v)}</td></tr>'
                   for k, v in (payload.get('headers') or {}).items()]
    return ('<!doctype html><html><head><meta charset="utf-8">'
            '<title>sg-sentinel httpget</title></head><body>'
            '<h1>sg-sentinel httpget — request echo</h1>'
            '<table border="1" cellpadding="4">' + ''.join(rows) + '</table>'
            '<h2>headers</h2><table border="1" cellpadding="4">' + ''.join(header_rows) + '</table>'
            '</body></html>')


def wants_html(headers: dict, querystring: str) -> bool:
    if 'format=html' in (querystring or ''):
        return True
    accept = ''
    for k, v in (headers or {}).items():
        if str(k).lower() == 'accept':
            accept = str(v)
    return 'text/html' in accept and 'application/json' not in accept
