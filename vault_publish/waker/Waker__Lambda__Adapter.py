# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish — Waker__Lambda__Adapter
# The only edge-specific code in the package. CloudFront fails over to the waker
# Lambda for a cold slug; the Lambda runs the vault-publish FastAPI app behind
# the Lambda Web Adapter. This adapter is the thin translation layer: extract
# the slug from the Host header, run the wake sequence, and produce the warming
# page when the instance is not yet healthy.
#
# The Lambda handler wiring (Lambda Web Adapter, Function URL event shape) is the
# marked seam — handle() and slug_from_host() are the pure, testable core.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                         import Type_Safe

from vault_publish.schemas.Schema__VaultPublish__Wake__Response import Schema__VaultPublish__Wake__Response
from vault_publish.service.Publish__Service                  import Publish__Service, SGRAPH_APP_DOMAIN


class Waker__Lambda__Adapter(Type_Safe):
    service : Publish__Service

    def slug_from_host(self, host: str) -> str:
        # 'sara-cv.sgraph.app'        → 'sara-cv'
        # 'sara-cv.qa.sgraph.app'     → 'sara-cv'   (env wildcard — slug is still the first label)
        # 'sgraph.app' / unrelated    → ''          (no slug)
        host  = str(host).strip().lower().split(':')[0]                      # drop any :port
        parts = host.split('.')
        if not host.endswith(SGRAPH_APP_DOMAIN):
            return ''
        if len(parts) < 3:                                                   # bare apex — no slug label
            return ''
        return parts[0]

    def handle(self, host: str) -> Schema__VaultPublish__Wake__Response:
        slug = self.slug_from_host(host)
        return self.service.wake(slug)

    def warming_page_html(self, response: Schema__VaultPublish__Wake__Response) -> str:
        # An auto-refreshing page — not an HTTP redirect. The Lambda handler
        # serves this with Cache-Control: no-cache so CloudFront does not pin it.
        slug = str(response.slug) or 'your vault'
        return ('<!doctype html><html><head><meta charset="utf-8">'
                '<meta http-equiv="refresh" content="3">'
                f'<title>Starting {slug}</title></head>'
                '<body style="font-family:sans-serif;text-align:center;padding:4rem">'
                f'<h1>Starting {slug}…</h1>'
                '<p>Your vault is waking up — this usually takes about 20 seconds.</p>'
                f'<p style="color:#888">{response.detail}</p>'
                '</body></html>')
