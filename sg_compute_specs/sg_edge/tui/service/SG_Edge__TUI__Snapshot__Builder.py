# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: SG_Edge__TUI__Snapshot__Builder
# Builds the one normalised Schema__SG_Edge__TUI__Snapshot from a SG_Edge__DNS__
# Helper. The SAME routine serves both sources — the local stack injects a helper
# over the file-backed local DNS, the AWS source injects one over real Route 53 —
# so local and edge render identically (the snapshot seam the plan calls for).
#
# It reads only DNS-grounded state (zone / wildcard / fleet / counter / slugs) and
# derives deviation issues with source-agnostic rules. No cost/throughput/instance
# data is invented — those panes stay absent from capabilities until Slice 5.
# A missing zone is read as "not provisioned" (guarded before any get_record, which
# would otherwise raise on an absent zone).
# ═══════════════════════════════════════════════════════════════════════════════

import time
from typing import Optional

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.aws.dns.enums.Enum__Route53__Record_Type     import Enum__Route53__Record_Type
from sg_compute_specs.sg_edge.service.SG_Edge__DNS__Helper                          import SG_Edge__DNS__Helper
from sg_compute_specs.sg_edge.local.enums.Enum__Local__Edge__Severity               import Enum__Local__Edge__Severity
from sg_compute_specs.sg_edge.local.schemas.Schema__Local__Edge__Issue              import Schema__Local__Edge__Issue
from sg_compute_specs.sg_edge.tui.enums.Enum__SG_Edge__TUI__Slug_State              import Enum__SG_Edge__TUI__Slug_State
from sg_compute_specs.sg_edge.tui.enums.Enum__SG_Edge__TUI__Target                  import Enum__SG_Edge__TUI__Target
from sg_compute_specs.sg_edge.tui.schemas.Schema__SG_Edge__TUI__Slug                import Schema__SG_Edge__TUI__Slug
from sg_compute_specs.sg_edge.tui.schemas.Schema__SG_Edge__TUI__Snapshot            import Schema__SG_Edge__TUI__Snapshot
from sg_compute_specs.sg_edge.tui.sg_edge_tui__config                               import REAL_CAPABILITIES

A        = Enum__Route53__Record_Type.A
RESERVED = {'proxies', '*', '_state'}                                                # A-record labels that are not slugs


class SG_Edge__TUI__Snapshot__Builder(Type_Safe):

    def build(self, helper      : SG_Edge__DNS__Helper,
                    target      : Enum__SG_Edge__TUI__Target,
                    parent      : str,
                    deployed    : Optional[bool] = None) -> Schema__SG_Edge__TUI__Snapshot:
        route53  = helper.route53
        snapshot = Schema__SG_Edge__TUI__Snapshot(parent=parent, target=target, captured_at=int(time.time()))
        for capability in REAL_CAPABILITIES:
            snapshot.capabilities.append(capability)

        zone_exists         = route53.find_hosted_zone_by_name(parent) is not None
        snapshot.zone_exists = zone_exists
        snapshot.deployed    = zone_exists if deployed is None else deployed          # aws: zone presence; local: stack marker
        if not zone_exists:                                                          # nothing else is readable without a zone
            self.evaluate_issues(snapshot)
            return snapshot

        snapshot.wildcard    = route53.get_record(parent, f'*.{parent}', A) is not None
        snapshot.zero_streak = int(helper.read_state(parent).zero_streak)
        for ip in helper.list_proxy_ips(parent):
            snapshot.fleet_ips.append(ip)

        labels = sorted(set(self.registered_a_slugs(route53, parent)) | set(helper.list_active_slugs(parent)))
        for label in labels:
            snapshot.slugs.append(self.slug_view(helper, parent, label))

        self.evaluate_issues(snapshot)
        return snapshot

    def registered_a_slugs(self, route53, parent : str) -> list:                     # <slug>.<parent> A records (excludes proxies/*/_state and the bare parent)
        suffix = f'.{parent}'
        slugs  = []
        for record in route53.list_records(parent):
            if str(record.record_type) != str(A):
                continue
            name = str(record.name).rstrip('.').replace('\\052', '*')
            if name.endswith(suffix):
                label = name[:-len(suffix)]
                if label and label not in RESERVED and '.' not in label:
                    slugs.append(label)
        return sorted(set(slugs))

    def slug_view(self, helper : SG_Edge__DNS__Helper, parent : str, label : str) -> Schema__SG_Edge__TUI__Slug:
        has_a   = helper.route53.get_record(parent, f'{label}.{parent}', A) is not None
        routing = helper.read_routing(parent, label)
        if   has_a and routing : state = Enum__SG_Edge__TUI__Slug_State.LIVE
        elif has_a             : state = Enum__SG_Edge__TUI__Slug_State.DORMANT
        else                   : state = Enum__SG_Edge__TUI__Slug_State.ORPHAN_BACKEND
        return Schema__SG_Edge__TUI__Slug(slug         = label,
                                          fqdn         = f'{label}.{parent}',
                                          state        = state,
                                          backend_ip   = str(routing.ip)   if routing else '',
                                          backend_port = int(routing.port) if routing else 0)

    def evaluate_issues(self, snapshot : Schema__SG_Edge__TUI__Snapshot) -> None:    # source-agnostic deviation rules (no stack-marker concept)
        issues = snapshot.issues

        def add(severity, area, message):
            issues.append(Schema__Local__Edge__Issue(severity=severity, area=area, message=message))

        if not snapshot.zone_exists:
            add(Enum__Local__Edge__Severity.INFO, 'edge', f'edge not provisioned — no hosted zone for {snapshot.parent}.')
            return
        if not snapshot.wildcard:
            add(Enum__Local__Edge__Severity.ERROR, 'wildcard', f'*.{snapshot.parent} A record missing (CloudFront equivalent).')
        if len(snapshot.fleet_ips) == 0:
            add(Enum__Local__Edge__Severity.ERROR, 'fleet', 'proxies.<parent> has no IPs — the proxy fleet is empty.')
        for slug in snapshot.slugs:
            if slug.state == Enum__SG_Edge__TUI__Slug_State.ORPHAN_BACKEND:
                add(Enum__Local__Edge__Severity.WARN, f'slug:{slug.slug}',
                    'backend TXT present but no registration A record (orphan backend).')
            elif slug.state == Enum__SG_Edge__TUI__Slug_State.DORMANT:
                add(Enum__Local__Edge__Severity.INFO, f'slug:{slug.slug}',
                    'registered but dormant (no backend) — first request triggers the Vault Waker.')
        if not issues:
            add(Enum__Local__Edge__Severity.OK, 'edge', 'all checks passed — edge is provisioned and healthy.')
