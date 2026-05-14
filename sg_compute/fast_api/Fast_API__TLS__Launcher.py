# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Fast_API__TLS__Launcher
# The §8.2 TLS launch contract. Reads the FAST_API__TLS__* env vars and runs a
# FastAPI app under uvicorn — plain HTTP on :8000 by default, or HTTPS on the
# configured port with a cert+key when FAST_API__TLS__ENABLED is truthy.
#
# Contract (Q8: explicit flag, not implicit file-presence):
#   FAST_API__TLS__ENABLED    false   master switch — default off keeps the
#                                     one-image / five-targets guarantee intact
#                                     (Lambda / CI / laptop run plain HTTP)
#   FAST_API__TLS__CERT_FILE  /certs/cert.pem
#   FAST_API__TLS__KEY_FILE   /certs/key.pem
#   FAST_API__TLS__PORT       443
#
# Enabled-but-cert-missing fails loud (assert) — never a silent HTTP fallback.
# The one-shot cert sidecar + compose `depends_on` guarantees the files exist.
#
# Single-file by intent: this is destined for upstream OSBot__Fast_API, so the
# lift should be mechanical (Q10).
# ═══════════════════════════════════════════════════════════════════════════════

import os

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute.fast_api.Schema__Fast_API__TLS__Config import Schema__Fast_API__TLS__Config

ENV__ENABLED   = 'FAST_API__TLS__ENABLED'
ENV__CERT_FILE = 'FAST_API__TLS__CERT_FILE'
ENV__KEY_FILE  = 'FAST_API__TLS__KEY_FILE'
ENV__PORT      = 'FAST_API__TLS__PORT'

DEFAULT__CERT_FILE = '/certs/cert.pem'
DEFAULT__KEY_FILE  = '/certs/key.pem'
DEFAULT__TLS_PORT  = 443
DEFAULT__HTTP_PORT = 8000

_TRUTHY = {'1', 'true', 'yes', 'on'}


class Fast_API__TLS__Launcher(Type_Safe):

    def config_from_env(self) -> Schema__Fast_API__TLS__Config:
        enabled = os.environ.get(ENV__ENABLED, '').strip().lower() in _TRUTHY
        if not enabled:
            return Schema__Fast_API__TLS__Config(enabled=False, port=DEFAULT__HTTP_PORT)
        return Schema__Fast_API__TLS__Config(
            enabled   = True                                                  ,
            port      = int(os.environ.get(ENV__PORT) or DEFAULT__TLS_PORT)   ,
            cert_file = os.environ.get(ENV__CERT_FILE) or DEFAULT__CERT_FILE  ,
            key_file  = os.environ.get(ENV__KEY_FILE)  or DEFAULT__KEY_FILE   )

    def assert_ready(self, config: Schema__Fast_API__TLS__Config) -> None:
        if not config.enabled:
            return
        assert os.path.isfile(config.cert_file), (
            f'{ENV__ENABLED} is on but cert file is missing: {config.cert_file!r} — '
            f'the one-shot cert sidecar must run first')
        assert os.path.isfile(config.key_file), (
            f'{ENV__ENABLED} is on but key file is missing: {config.key_file!r} — '
            f'the one-shot cert sidecar must run first')

    def uvicorn_kwargs(self, config: Schema__Fast_API__TLS__Config) -> dict:
        kwargs = {'host': config.host, 'port': config.port}
        if config.enabled:
            kwargs['ssl_certfile'] = config.cert_file
            kwargs['ssl_keyfile']  = config.key_file
        return kwargs

    def serve(self, app) -> None:
        import uvicorn
        config = self.config_from_env()
        self.assert_ready(config)
        uvicorn.run(app, **self.uvicorn_kwargs(config))
