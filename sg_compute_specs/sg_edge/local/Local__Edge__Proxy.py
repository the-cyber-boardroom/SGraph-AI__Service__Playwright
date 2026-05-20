# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge local: Local__Edge__Proxy
# The local proxy's request logic — the Python equivalent of the Phase 2 OpenResty
# Lua hot path, used by the local stack so the end-to-end flow runs with no AWS and
# no docker. Given a Host header it:
#   1. extracts the slug (first DNS label)
#   2. reads <slug>.<parent> A   — absent → "slug not recognised" (404)
#   3. reads _sg.<slug>.<parent> TXT — absent → registered-but-dormant (503 loading)
#   4. both present → serves "Welcome to the <slug> vault" (200), recording slug_seen
#
# All DNS reads go through the injected SG_Edge__DNS__Helper, so the same logic runs
# against the file-backed local DNS or (later) real Route 53.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.aws.dns.enums.Enum__Route53__Record_Type     import Enum__Route53__Record_Type
from sg_compute_specs.sg_edge.service.SG_Edge__DNS__Helper                          import SG_Edge__DNS__Helper
from sg_compute_specs.sg_edge.local.enums.Enum__Local__Edge__Response_Kind          import Enum__Local__Edge__Response_Kind
from sg_compute_specs.sg_edge.local.schemas.Schema__Local__Edge__Response           import Schema__Local__Edge__Response
from sg_compute_specs.sg_edge.local.sg_edge_local__config                           import SG_EDGE__LOCAL_PARENT


class Local__Edge__Proxy(Type_Safe):
    dns    : SG_Edge__DNS__Helper
    parent : str = SG_EDGE__LOCAL_PARENT

    def slug_from_host(self, host: str) -> str:
        host = str(host).split(':')[0].strip().rstrip('.')                           # strip :port and trailing dot
        return host.split('.')[0] if host else ''

    def _a_registered(self, slug: str) -> bool:                                      # <slug>.<parent> A present == "slug is registered"
        try:                                                                         # a missing zone (edge not set up) reads as "not registered"
            record = self.dns.route53.get_record(self.parent, f'{slug}.{self.parent}',
                                                 Enum__Route53__Record_Type.A)
        except ValueError:
            return False
        return record is not None

    def handle(self, host: str) -> Schema__Local__Edge__Response:
        slug = self.slug_from_host(host)

        if not slug or not self._a_registered(slug):                                 # no A record → unknown slug
            return Schema__Local__Edge__Response(
                slug=slug, host=str(host), status_code=404,
                kind=Enum__Local__Edge__Response_Kind.NOT_RECOGNISED,
                title=f'slug not recognised: {slug or "(none)"}',
                body=self._page(f'slug not recognised',
                                f'<p>No vault is registered at <code>{host}</code>.</p>'))

        routing = self.dns.read_routing(self.parent, slug)
        if routing is None:                                                          # A but no TXT → registered, dormant
            return Schema__Local__Edge__Response(
                slug=slug, host=str(host), status_code=503,
                kind=Enum__Local__Edge__Response_Kind.DORMANT,
                title=f'{slug} vault is waking up',
                body=self._page(f'{slug} vault is waking up',
                                '<p>This vault is registered but has no live backend yet. '
                                'The Vault Waker is being triggered — this page would poll until ready.</p>'))

        backend = f'{routing.ip}:{int(routing.port)}'
        return Schema__Local__Edge__Response(
            slug=slug, host=str(host), status_code=200,
            kind=Enum__Local__Edge__Response_Kind.WELCOME,
            title=f'Welcome to the {slug} vault',
            backend=backend,
            body=self._page(f'Welcome to the {slug} vault',
                            f'<p>Served by the SG/Edge local proxy.</p>'
                            f'<ul><li>slug: <code>{slug}</code></li>'
                            f'<li>host: <code>{host}</code></li>'
                            f'<li>backend: <code>{backend}</code></li></ul>'))

    def _page(self, heading: str, inner: str) -> str:
        return (f'<!doctype html><meta charset="utf-8">'
                f'<title>{heading} — SG/Edge</title>'
                f'<h1>{heading}</h1>{inner}')
