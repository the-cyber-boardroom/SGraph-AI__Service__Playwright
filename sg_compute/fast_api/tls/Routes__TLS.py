# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Routes__TLS
# The slim public TLS surface served by Fast_API__TLS. Three jobs, no privilege:
#   GET  /tls/cert-info              decode the cert this app is serving
#   GET  /tls/secure-context-check   a self-contained browser page that evaluates
#                                    window.isSecureContext + Web Crypto and POSTs
#                                    the verdict back
#   POST /tls/secure-context-result  record what a browser reported
#   GET  /tls/secure-context-last    read back the last recorded report
#
# The recorded report is the PoC's pass/fail signal; `sp <spec> cert check`
# reads it without needing a human in a browser.
# ═══════════════════════════════════════════════════════════════════════════════

import os

from fastapi                                     import HTTPException
from fastapi.responses                           import HTMLResponse
from osbot_fast_api.api.routes.Fast_API__Routes  import Fast_API__Routes

from sg_compute.platforms.tls.Cert__Inspector              import Cert__Inspector
from sg_compute.platforms.tls.Schema__Secure_Context__Result import Schema__Secure_Context__Result

TAG__ROUTES_TLS = 'tls'

ENV__CERT_FILE     = 'FAST_API__TLS__CERT_FILE'
DEFAULT__CERT_FILE = '/certs/cert.pem'

_LAST_RESULT = {'recorded': False}                                           # in-memory; last browser report

_PAGE = '''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>SG · secure-context check</title>
  <style>
    body   { font-family: system-ui, sans-serif; max-width: 40rem; margin: 3rem auto; padding: 0 1rem; }
    .row   { display: flex; justify-content: space-between; padding: .6rem 0; border-bottom: 1px solid #eee; }
    .pass  { color: #0a0; font-weight: 700; }
    .fail  { color: #c00; font-weight: 700; }
    code   { background: #f4f4f4; padding: .1rem .3rem; border-radius: 3px; }
  </style>
</head>
<body>
  <h1>secure-context check</h1>
  <p>If both rows are <span class="pass">PASS</span>, this origin is a secure context
     and the Web Crypto API is available &mdash; the TLS PoC is green.</p>
  <div class="row"><code>window.isSecureContext</code><span id="ctx">&hellip;</span></div>
  <div class="row"><code>window.crypto.subtle</code><span id="crypto">&hellip;</span></div>
  <p id="reported" style="color:#888"></p>
  <script>
    var isSecure   = window.isSecureContext === true;
    var hasCrypto  = !!(window.crypto && window.crypto.subtle);
    function mark(id, ok) {
      var el = document.getElementById(id);
      el.textContent = ok ? 'PASS' : 'FAIL';
      el.className   = ok ? 'pass' : 'fail';
    }
    mark('ctx', isSecure);
    mark('crypto', hasCrypto);
    fetch('/tls/secure-context-result', {
      method  : 'POST',
      headers : { 'Content-Type': 'application/json' },
      body    : JSON.stringify({
        url               : window.location.href,
        user_agent        : navigator.userAgent,
        is_secure_context : isSecure,
        has_web_crypto    : hasCrypto,
        checked_at        : Date.now()
      })
    }).then(function () {
      document.getElementById('reported').textContent = 'result reported to the server';
    }).catch(function () {
      document.getElementById('reported').textContent = 'could not report result';
    });
  </script>
</body>
</html>
'''


class Routes__TLS(Fast_API__Routes):
    tag : str = TAG__ROUTES_TLS

    def cert_info(self) -> dict:
        path = os.environ.get(ENV__CERT_FILE) or DEFAULT__CERT_FILE
        if not os.path.isfile(path):
            raise HTTPException(status_code=503, detail=f'no cert at {path} — cert sidecar has not run yet')
        return Cert__Inspector().inspect_file(path).json()
    cert_info.__route_path__ = '/cert-info'

    def secure_context_check(self) -> HTMLResponse:
        return HTMLResponse(content=_PAGE)
    secure_context_check.__route_path__ = '/secure-context-check'

    def secure_context_result(self, body: Schema__Secure_Context__Result) -> dict:
        _LAST_RESULT.clear()
        _LAST_RESULT.update(body.json())
        _LAST_RESULT['recorded'] = True
        return {'recorded': True, 'is_secure_context': bool(body.is_secure_context)}
    secure_context_result.__route_path__ = '/secure-context-result'

    def secure_context_last(self) -> dict:
        return dict(_LAST_RESULT)
    secure_context_last.__route_path__ = '/secure-context-last'

    def setup_routes(self):
        self.add_route_get (self.cert_info             )
        self.add_route_get (self.secure_context_check  )
        self.add_route_post(self.secure_context_result )
        self.add_route_get (self.secure_context_last   )
