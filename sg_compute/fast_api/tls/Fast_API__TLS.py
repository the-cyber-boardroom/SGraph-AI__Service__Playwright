# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Fast_API__TLS
# The slim, unprivileged, public-facing TLS surface (Candidate B in the PoC
# doc). Extends osbot_fast_api.Fast_API — not Serverless__Fast_API — because it
# is a container sidecar, never a Lambda. It carries exactly one route class
# and NO api-key auth: the secure-context-check page is meant to be reachable
# by a browser with no credentials. The privileged host-plane stays internal.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_fast_api.api.Fast_API import Fast_API

from sg_compute.fast_api.tls.Routes__TLS import Routes__TLS


class Fast_API__TLS(Fast_API):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.config.enable_api_key = False                                   # public single-purpose surface — no auth by design

    def setup_routes(self):
        self.add_routes(Routes__TLS)
