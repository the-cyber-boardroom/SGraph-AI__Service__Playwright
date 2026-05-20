# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge: SG_Edge__DNS__Helper
# The Edge Waker's DNS surface, layered over the existing sg aws dns client
# (Route53__AWS__Client). Edge Waker state lives entirely in DNS (brief 02), so
# this helper owns the three record shapes the control plane touches:
#
#   proxies.<parent>   A    fleet membership — one record set, N IP values
#   _state.<parent>    TXT  idle-teardown counter (zero_streak;updated)
#   _sg.<slug>.<parent> TXT routing records — read-only here (count active vaults)
#
# It does NOT write _sg.<slug> routing records — those belong to the Vault Waker
# (Phase 2). All AWS access goes through the injected Route53__AWS__Client seam;
# unit tests inject Route53__AWS__Client__In_Memory (no mocks). TXT values are
# quoted on write / unquoted on read to match Route 53's wire format.
# ═══════════════════════════════════════════════════════════════════════════════

from typing import Optional

from osbot_utils.type_safe.Type_Safe                                                    import Type_Safe

from sgraph_ai_service_playwright__cli.aws.dns.enums.Enum__Route53__Record_Type         import Enum__Route53__Record_Type
from sgraph_ai_service_playwright__cli.aws.dns.schemas.Schema__Route53__Change__Result  import Schema__Route53__Change__Result
from sgraph_ai_service_playwright__cli.aws.dns.service.Route53__AWS__Client             import Route53__AWS__Client
from sg_compute_specs.sg_edge.schemas.Schema__SG_Edge__State__Record                    import Schema__SG_Edge__State__Record
from sg_compute_specs.sg_edge.schemas.Schema__SG_Edge__TXT__Record                      import Schema__SG_Edge__TXT__Record
from sg_compute_specs.sg_edge.service.SG_Edge__State__Builder                           import SG_Edge__State__Builder
from sg_compute_specs.sg_edge.service.SG_Edge__TXT__Builder                             import SG_Edge__TXT__Builder

PROXY_A_TTL    = 30                                                                      # short — a dead proxy's A record clears fast
STATE_TXT_TTL  = 30                                                                      # read on every idle-check; no need to cache long
ROUTING_PREFIX = '_sg.'                                                                  # _sg.<slug>.<parent>
STATE_LABEL    = '_state'                                                                # _state.<parent>
PROXIES_LABEL  = 'proxies'                                                               # proxies.<parent>


class SG_Edge__DNS__Helper(Type_Safe):
    route53       : Route53__AWS__Client                                                 # seam — tests inject Route53__AWS__Client__In_Memory
    txt_builder   : SG_Edge__TXT__Builder
    state_builder : SG_Edge__State__Builder

    # ── record-name composition ────────────────────────────────────────────────

    def proxies_name(self, parent : str) -> str:
        return f'{PROXIES_LABEL}.{parent}'

    def state_name(self, parent : str) -> str:
        return f'{STATE_LABEL}.{parent}'

    def routing_name(self, parent : str, slug : str) -> str:
        return f'{ROUTING_PREFIX}{slug}.{parent}'

    # ── proxy fleet membership (proxies.<parent> A) ─────────────────────────────

    def list_proxy_ips(self, parent : str) -> list:                                      # current fleet IPs (empty when no record)
        record = self.route53.get_record(parent, self.proxies_name(parent), Enum__Route53__Record_Type.A)
        return list(record.values) if record else []

    def proxy_count(self, parent : str) -> int:
        return len(self.list_proxy_ips(parent))

    def add_proxy_ip(self, parent : str, ip : str) -> Optional[Schema__Route53__Change__Result]:  # idempotent — None when ip already present
        ips = self.list_proxy_ips(parent)
        if ip in ips:
            return None
        ips.append(ip)
        return self.route53.upsert_record(parent, self.proxies_name(parent),
                                          Enum__Route53__Record_Type.A, ips, ttl=PROXY_A_TTL)

    def remove_proxy_ip(self, parent : str, ip : str) -> Optional[Schema__Route53__Change__Result]:  # None when ip absent; deletes the set when last ip removed
        ips = self.list_proxy_ips(parent)
        if ip not in ips:
            return None
        remaining = [x for x in ips if x != ip]
        if remaining:
            return self.route53.upsert_record(parent, self.proxies_name(parent),
                                              Enum__Route53__Record_Type.A, remaining, ttl=PROXY_A_TTL)
        return self.route53.delete_record(parent, self.proxies_name(parent), Enum__Route53__Record_Type.A)

    # ── teardown counter (_state.<parent> TXT) ──────────────────────────────────

    def read_state(self, parent : str) -> Schema__SG_Edge__State__Record:                # absent / malformed -> fresh zeroed record
        record = self.route53.get_record(parent, self.state_name(parent), Enum__Route53__Record_Type.TXT)
        if record is None or not record.values:
            return Schema__SG_Edge__State__Record()
        parsed = self.state_builder.try_parse(self._unquote(record.values[0]))
        return parsed if parsed is not None else Schema__SG_Edge__State__Record()

    def write_state(self, parent : str, state : Schema__SG_Edge__State__Record) -> Schema__Route53__Change__Result:
        txt = self.state_builder.build(state)
        return self.route53.upsert_record(parent, self.state_name(parent),
                                          Enum__Route53__Record_Type.TXT, [self._quote(txt)], ttl=STATE_TXT_TTL)

    # ── active vaults (_sg.<slug>.<parent> TXT — read-only) ──────────────────────

    def list_active_slugs(self, parent : str) -> list:                                   # slugs that currently have a routing TXT record
        suffix = f'.{parent}'
        slugs  = []
        for record in self.route53.list_records(parent):
            if str(record.record_type) != str(Enum__Route53__Record_Type.TXT):
                continue
            name = str(record.name).rstrip('.')
            if name.startswith(ROUTING_PREFIX) and name.endswith(suffix):                 # _state.<parent> starts with _state, never matches _sg.
                slug = name[len(ROUTING_PREFIX):-len(suffix)]
                if slug:
                    slugs.append(slug)
        return slugs

    def active_slug_count(self, parent : str) -> int:
        return len(self.list_active_slugs(parent))

    def read_routing(self, parent : str, slug : str) -> Optional[Schema__SG_Edge__TXT__Record]:  # parse one _sg.<slug> TXT; None when absent/malformed
        record = self.route53.get_record(parent, self.routing_name(parent, slug), Enum__Route53__Record_Type.TXT)
        if record is None or not record.values:
            return None
        return self.txt_builder.try_parse(self._unquote(record.values[0]))

    # ── internal ────────────────────────────────────────────────────────────────

    def _quote(self, value : str) -> str:                                                # Route 53 stores TXT character-strings double-quoted
        return f'"{value}"'

    def _unquote(self, value : str) -> str:                                              # strip the surrounding quotes Route 53 returns
        v = str(value).strip()
        if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
            return v[1:-1]
        return v
