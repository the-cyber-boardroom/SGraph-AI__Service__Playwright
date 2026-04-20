# ═══════════════════════════════════════════════════════════════════════════════
# Agent Mitmproxy — Routes__CA
#
#   GET /ca/cert — returns the mitmproxy CA cert PEM (application/x-pem-file).
#                  503 when the file doesn't exist (mitmweb writes it on first
#                  start; race window is tiny but handled explicitly).
#   GET /ca/info — parses the PEM and returns fingerprint + validity dates.
#
# The PEM path is taken from env AGENT_MITMPROXY__CA_CERT_PATH, defaulting to
# /root/.mitmproxy/mitmproxy-ca-cert.pem (mitmweb's default confdir).
# ═══════════════════════════════════════════════════════════════════════════════

import os

from fastapi                                                                             import HTTPException
from fastapi.responses                                                                   import Response
from osbot_fast_api.api.routes.Fast_API__Routes                                          import Fast_API__Routes
from osbot_utils.utils.Env                                                               import get_env

from agent_mitmproxy.consts                                                              import env_vars, paths
from agent_mitmproxy.schemas.ca.Schema__CA__Cert__Info                                   import Schema__CA__Cert__Info


TAG__ROUTES_CA   = 'ca'
ROUTES_PATHS__CA = [f'/{TAG__ROUTES_CA}/cert', f'/{TAG__ROUTES_CA}/info']

MEDIA_TYPE__PEM  = 'application/x-pem-file'


def _resolve_ca_path() -> str:
    return get_env(env_vars.ENV_VAR__CA_CERT_PATH) or paths.PATH__CA_CERT_PEM


def _read_pem_bytes() -> bytes:
    ca_path = _resolve_ca_path()
    if not os.path.isfile(ca_path):
        raise HTTPException(status_code=503, detail=f'CA cert not yet written to {ca_path} — mitmweb must boot once before it exists')
    with open(ca_path, 'rb') as f:
        return f.read()


class Routes__CA(Fast_API__Routes):
    tag : str = TAG__ROUTES_CA

    def cert(self) -> Response:                                                      # Streamed as-is; operator pipes into update-ca-certificates
        return Response(content=_read_pem_bytes(), media_type=MEDIA_TYPE__PEM)

    def info(self) -> Schema__CA__Cert__Info:
        from cryptography                    import x509
        from cryptography.hazmat.primitives  import hashes

        ca_path  = _resolve_ca_path()
        pem_bytes = _read_pem_bytes()
        cert      = x509.load_pem_x509_certificate(pem_bytes)
        digest    = cert.fingerprint(hashes.SHA256())
        finger    = ':'.join(f'{b:02X}' for b in digest)

        return Schema__CA__Cert__Info(path               = ca_path                                      ,
                                      size_bytes         = len(pem_bytes)                               ,
                                      fingerprint_sha256 = finger                                       ,
                                      not_before         = int(cert.not_valid_before_utc.timestamp() * 1000),
                                      not_after          = int(cert.not_valid_after_utc.timestamp()  * 1000))

    def setup_routes(self):
        self.add_route_get(self.cert)
        self.add_route_get(self.info)
