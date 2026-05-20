# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge local: Local__Edge__Stack
# Orchestrates the local edge deployment: setup → register slugs → request →
# check → teardown, all against the file-backed local DNS (no AWS, no docker).
#
# It plays two roles at once for the local simulation:
#   • Edge Waker  — writes proxies.<parent> A + _state.<parent> TXT on setup
#   • Vault Waker — writes <slug>.<parent> A (registration) + _sg.<slug> TXT
#                   (backend) on register; removes them on unregister
# so the full Phase-1 + Phase-2 record lifecycle is exercisable end-to-end.
#
# All DNS work reuses the existing SG_Edge__DNS__Helper / SG_Edge__TXT__Builder; a
# fresh Local__Route53__Client is built per call so every operation reads the
# on-disk DNS file (cross-process consistency) and writes it back.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import os
import time

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.aws.dns.enums.Enum__Route53__Record_Type     import Enum__Route53__Record_Type
from sg_compute_specs.sg_edge.schemas.Schema__SG_Edge__State__Record                import Schema__SG_Edge__State__Record
from sg_compute_specs.sg_edge.schemas.Schema__SG_Edge__TXT__Record                  import Schema__SG_Edge__TXT__Record
from sg_compute_specs.sg_edge.service.SG_Edge__DNS__Helper                          import SG_Edge__DNS__Helper
from sg_compute_specs.sg_edge.service.SG_Edge__TXT__Builder                         import SG_Edge__TXT__Builder
from sg_compute_specs.sg_edge.local.Local__Route53__Client                          import Local__Route53__Client
from sg_compute_specs.sg_edge.local.Local__Edge__Proxy                              import Local__Edge__Proxy
from sg_compute_specs.sg_edge.local.enums.Enum__Local__Edge__Severity               import Enum__Local__Edge__Severity
from sg_compute_specs.sg_edge.local.schemas.Schema__Local__Edge__Issue              import Schema__Local__Edge__Issue
from sg_compute_specs.sg_edge.local.schemas.Schema__Local__Edge__Response           import Schema__Local__Edge__Response
from sg_compute_specs.sg_edge.local.schemas.Schema__Local__Edge__Slug               import Schema__Local__Edge__Slug
from sg_compute_specs.sg_edge.local.schemas.Schema__Local__Edge__Status             import Schema__Local__Edge__Status
from sg_compute_specs.sg_edge.local.sg_edge_local__config                           import (
    SG_EDGE__LOCAL_PARENT, LOCAL_PROXY_IP, LOCAL_BACKEND_IP, LOCAL_BACKEND_PORT,
    local_dns_path, local_stack_path)

A   = Enum__Route53__Record_Type.A
TXT = Enum__Route53__Record_Type.TXT


class Local__Edge__Stack(Type_Safe):
    parent    : str = SG_EDGE__LOCAL_PARENT
    state_dir : str = ''                                                             # '' → config default (~/.sg/edge_local)

    # ── path resolution ───────────────────────────────────────────────────────────

    def dns_path(self) -> str:
        return os.path.join(self.state_dir, 'dns.json') if self.state_dir else local_dns_path()

    def stack_path(self) -> str:
        return os.path.join(self.state_dir, 'stack.json') if self.state_dir else local_stack_path()

    def _client(self) -> Local__Route53__Client:
        return Local__Route53__Client(dns_path=self.dns_path())

    def _helper(self, client: Local__Route53__Client = None) -> SG_Edge__DNS__Helper:
        return SG_Edge__DNS__Helper(route53=client or self._client())

    # ── lifecycle ───────────────────────────────────────────────────────────────

    def is_deployed(self) -> bool:
        return os.path.isfile(self.stack_path())

    def setup(self) -> Schema__Local__Edge__Status:                                  # idempotent — Edge Waker's job: zone + wildcard + one proxy + counter
        client = self._client()
        client.ensure_zone(self.parent)
        client.upsert_record(self.parent, f'*.{self.parent}', A, [LOCAL_PROXY_IP], ttl=300)
        helper = self._helper(client)
        helper.add_proxy_ip(self.parent, LOCAL_PROXY_IP)
        helper.write_state(self.parent, Schema__SG_Edge__State__Record(zero_streak=0, updated=int(time.time())))
        self._write_marker()
        return self.status()

    def register(self, slug: str, with_backend: bool = True) -> Schema__Local__Edge__Slug:  # Vault Waker's job: A (registration) + TXT (backend)
        client = self._client()
        client.ensure_zone(self.parent)                                              # tolerate register-before-setup (check flags the missing wildcard/fleet)
        client.upsert_record(self.parent, f'{slug}.{self.parent}', A, [LOCAL_PROXY_IP], ttl=300)
        if with_backend:
            txt = SG_Edge__TXT__Builder().build(Schema__SG_Edge__TXT__Record(
                ip=LOCAL_BACKEND_IP, port=LOCAL_BACKEND_PORT, launched=int(time.time())))
            client.upsert_record(self.parent, f'_sg.{slug}.{self.parent}', TXT, [f'"{txt}"'], ttl=30)
        return self.slug_view(slug)

    def unregister(self, slug: str) -> bool:                                         # remove A + TXT; True if anything was removed
        client  = self._client()
        if client.find_hosted_zone_by_name(self.parent) is None:                     # no zone → nothing to remove
            return False
        removed = False
        for name, rtype in [(f'{slug}.{self.parent}', A), (f'_sg.{slug}.{self.parent}', TXT)]:
            if client.get_record(self.parent, name, rtype) is not None:
                client.delete_record(self.parent, name, rtype)
                removed = True
        return removed

    def handle(self, host: str) -> Schema__Local__Edge__Response:                    # route a raw Host header through the local proxy
        return Local__Edge__Proxy(dns=self._helper(), parent=self.parent).handle(host)

    def request(self, slug: str) -> Schema__Local__Edge__Response:                   # simulate one user request end-to-end (in-process)
        return self.handle(f'{slug}.{self.parent}')

    def teardown(self) -> bool:                                                      # destroy the local edge; True if anything was removed
        removed = False
        for path in (self.dns_path(), self.stack_path()):
            if os.path.isfile(path):
                os.remove(path)
                removed = True
        return removed

    # ── introspection ─────────────────────────────────────────────────────────────

    def registered_slugs(self) -> list:                                             # slugs with a <slug>.<parent> A record (excludes proxies/*/_state)
        client   = self._client()
        if client.find_hosted_zone_by_name(self.parent) is None:                     # no zone yet → no slugs
            return []
        suffix   = f'.{self.parent}'
        reserved = {'proxies', '*', '_state'}
        slugs    = []
        for record in client.list_records(self.parent):
            if str(record.record_type) != str(A):
                continue
            name = str(record.name).rstrip('.').replace('\\052', '*')
            if name.endswith(suffix):
                label = name[:-len(suffix)]
                if label and label not in reserved and '.' not in label:
                    slugs.append(label)
        return sorted(set(slugs))

    def slug_view(self, slug: str) -> Schema__Local__Edge__Slug:
        client  = self._client()
        helper  = self._helper(client)
        has_a   = client.get_record(self.parent, f'{slug}.{self.parent}', A) is not None
        routing = helper.read_routing(self.parent, slug)
        return Schema__Local__Edge__Slug(
            slug=slug, fqdn=f'{slug}.{self.parent}', has_a=has_a,
            has_txt=routing is not None,
            backend_ip=str(routing.ip) if routing else '',
            backend_port=int(routing.port) if routing else 0)

    def status(self) -> Schema__Local__Edge__Status:
        client      = self._client()
        zone_exists = client.find_hosted_zone_by_name(self.parent) is not None
        status      = Schema__Local__Edge__Status(parent      = self.parent      ,
                                                  deployed    = self.is_deployed(),
                                                  zone_exists = zone_exists       )
        if not zone_exists:                                                          # nothing else is readable without a zone (before setup / after teardown)
            return status
        helper             = self._helper(client)
        status.wildcard    = client.get_record(self.parent, f'*.{self.parent}', A) is not None
        status.zero_streak = int(helper.read_state(self.parent).zero_streak)
        for ip in helper.list_proxy_ips(self.parent):
            status.proxy_ips.append(ip)
        labels = set(self.registered_slugs()) | set(helper.list_active_slugs(self.parent))
        for slug in sorted(labels):
            status.slugs.append(self.slug_view(slug))
        return status

    def check(self) -> Schema__Local__Edge__Status:                                  # status + deviation findings
        status = self.status()
        issues = status.issues

        def add(sev, area, msg):
            issues.append(Schema__Local__Edge__Issue(severity=sev, area=area, message=msg))

        if not status.deployed:
            if status.zone_exists or len(status.slugs):
                add(Enum__Local__Edge__Severity.WARN, 'stack',
                    'DNS records exist but no stack marker — run `sg edge local setup` (or teardown to clean up).')
            else:
                add(Enum__Local__Edge__Severity.INFO, 'stack', 'not deployed — run `sg edge local setup`.')
            return status

        if not status.zone_exists:
            add(Enum__Local__Edge__Severity.ERROR, 'dns-zone', f'hosted zone {status.parent} is missing.')
        if not status.wildcard:
            add(Enum__Local__Edge__Severity.ERROR, 'wildcard', f'*.{status.parent} A record missing (CloudFront equivalent).')
        if len(status.proxy_ips) == 0:
            add(Enum__Local__Edge__Severity.ERROR, 'fleet', 'proxies.<parent> has no IPs — the proxy fleet is empty.')

        for slug in status.slugs:
            if slug.has_txt and not slug.has_a:
                add(Enum__Local__Edge__Severity.WARN, f'slug:{slug.slug}',
                    'backend TXT present but no registration A record (orphan backend).')
            elif slug.has_a and not slug.has_txt:
                add(Enum__Local__Edge__Severity.INFO, f'slug:{slug.slug}',
                    'registered but dormant (no backend) — first request triggers the Vault Waker.')

        if not issues:
            add(Enum__Local__Edge__Severity.OK, 'edge', 'all checks passed — edge is deployed and healthy.')
        return status

    # ── internal ──────────────────────────────────────────────────────────────────

    def _write_marker(self) -> None:
        path = self.stack_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if os.path.isfile(path):
            return
        with open(path, 'w') as f:
            f.write(json.dumps({'parent': self.parent, 'created_at': int(time.time())}, indent=2))
