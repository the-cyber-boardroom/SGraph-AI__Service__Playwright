# mitmproxy interceptor -- replace text in HTML responses.
# Push to a running stack with:
#   sp firefox set-interceptor --interceptor-script scripts/interceptors/html_replace.py

from mitmproxy import http

# -- edit these ---------------------------------------------------------------

REPLACEMENTS = [
    ("Hello",  "G'day" ),   # word swap
    ("Google", "Boogle"),   # brand rename
]

# -----------------------------------------------------------------------------


def response(flow: http.HTTPFlow) -> None:
    if not flow.response:
        return
    ct = flow.response.headers.get("content-type", "")
    if "text/html" not in ct:
        return

    try:
        body = flow.response.get_text(strict=False)
    except Exception:
        return

    original = body
    for old, new in REPLACEMENTS:
        body = body.replace(old, new)

    if body != original:
        flow.response.set_text(body)
        print(f"[html_replace] patched {flow.request.pretty_url}")
