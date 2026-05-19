# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/ec2 — VPC__Stack__Provisioner
# Orchestrates Slice 1/2 EC2 primitives into a single end-to-end VPC stack:
# VPC → IGW → attach → RT → route(0/0→IGW) → 2 public subnets → public-IP-on-launch
# → associate RT → SG with ingress rules → tag-propagation.
# Idempotent: re-running with the same stack_name finds resources by the
#   Stack=<stack_name> tag and SKIPs phases that already match.
# Best-effort rollback: on first phase ERROR, the resources actually created in
#   this run are deleted in reverse order. Rollback failures are collected into
#   report.rollback_errors — they never raise.
# ═══════════════════════════════════════════════════════════════════════════════

import ipaddress
from datetime import datetime, timezone
from typing   import Optional

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws._shared.Phase__Timer                                  import Phase__Timer
from sgraph_ai_service_playwright__cli.aws._shared.collections.List__Schema__AWS__Phase__Result  import List__Schema__AWS__Phase__Result
from sgraph_ai_service_playwright__cli.aws._shared.collections.List__Str                         import List__Str
from sgraph_ai_service_playwright__cli.aws._shared.enums.Enum__AWS__Phase__Status                import Enum__AWS__Phase__Status
from sgraph_ai_service_playwright__cli.aws.ec2.collections.List__Schema__VPC__Stack__Ingress_Rule import List__Schema__VPC__Stack__Ingress_Rule
from sgraph_ai_service_playwright__cli.aws.ec2.enums.Enum__VPC__Stack__Phase                     import Enum__VPC__Stack__Phase
from sgraph_ai_service_playwright__cli.aws.ec2.schemas.Schema__VPC__Stack__Detail                import Schema__VPC__Stack__Detail
from sgraph_ai_service_playwright__cli.aws.ec2.schemas.Schema__VPC__Stack__Ingress_Rule          import Schema__VPC__Stack__Ingress_Rule
from sgraph_ai_service_playwright__cli.aws.ec2.schemas.Schema__VPC__Stack__Report                import Schema__VPC__Stack__Report
from sgraph_ai_service_playwright__cli.aws.ec2.schemas.Schema__VPC__Stack__Request               import Schema__VPC__Stack__Request


# default ingress rules: HTTP, HTTPS, and 8080 from 0.0.0.0/0
_DEFAULT_INGRESS_PORTS = (80, 443, 8080)
_DEFAULT_AZS           = ('a', 'b')                                                # fallback suffix list when ec2 has no describe_availability_zones method


class VPC__Stack__Provisioner(Type_Safe):
    ec2_client  : object = None
    progress_cb : object = None                                                    # callable(phase_name, status, detail='') or None

    # ── public ────────────────────────────────────────────────────────────────

    def default_ingress_rules(self) -> List__Schema__VPC__Stack__Ingress_Rule:
        rules = List__Schema__VPC__Stack__Ingress_Rule()
        for port in _DEFAULT_INGRESS_PORTS:
            rules.append(Schema__VPC__Stack__Ingress_Rule(
                protocol   = 'tcp',
                from_port  = port,
                to_port    = port,
                cidr_block = '0.0.0.0/0',
            ))
        return rules

    def create_stack(self, request: Schema__VPC__Stack__Request) -> Schema__VPC__Stack__Report:
        stack_name = request.stack_name
        report = Schema__VPC__Stack__Report(operation='create', stack_name=stack_name)
        timer  = Phase__Timer(progress_cb=self.progress_cb)
        # Resources we created this run — rollback walks this list in reverse.
        created_now = {'vpc': '', 'igw': '', 'rtb': '', 'sg': '',
                       'subnets': [], 'attach_vpc_for_igw': '',
                       'route_to_igw_rtb': '', 'rtb_assocs': []}

        # ── pre-flight: build the effective ingress-rules list ───────────────
        ingress_rules = request.ingress_rules
        if not ingress_rules or len(ingress_rules) == 0:
            ingress_rules = self.default_ingress_rules()

        try:
            # ── VPC ────────────────────────────────────────────────────────────
            with timer.phase(Enum__VPC__Stack__Phase.VPC.value) as phase:
                existing = self._find_resource_by_tag(self.ec2_client.list_vpcs(), stack_name)
                if existing is not None:
                    vpc_id = str(existing.vpc_id)
                    phase.detail = f'reused {vpc_id}'
                    phase.status = Enum__AWS__Phase__Status.SKIPPED
                else:
                    vpc = self.ec2_client.create_vpc(
                        cidr=request.cidr,
                        tags=self._stack_tags(stack_name, role='vpc'))
                    vpc_id = str(vpc.vpc_id)
                    created_now['vpc'] = vpc_id
                    phase.detail = f'created {vpc_id}'
            report.vpc_id = vpc_id

            # ── VPC_ATTRIBUTES ─────────────────────────────────────────────────
            with timer.phase(Enum__VPC__Stack__Phase.VPC_ATTRIBUTES.value) as phase:
                self.ec2_client.modify_vpc_attribute(vpc_id,
                                                      enable_dns_support  =True,
                                                      enable_dns_hostnames=True)
                phase.detail = 'dns_support=on, dns_hostnames=on'

            # ── INTERNET_GATEWAY ───────────────────────────────────────────────
            with timer.phase(Enum__VPC__Stack__Phase.INTERNET_GATEWAY.value) as phase:
                existing_igw = self._find_resource_by_tag(self.ec2_client.list_internet_gateways(), stack_name)
                if existing_igw is not None:
                    igw_id = str(existing_igw.igw_id)
                    phase.detail = f'reused {igw_id}'
                    phase.status = Enum__AWS__Phase__Status.SKIPPED
                else:
                    igw = self.ec2_client.create_internet_gateway(
                        tags=self._stack_tags(stack_name, role='igw'))
                    igw_id = str(igw.igw_id)
                    created_now['igw'] = igw_id
                    phase.detail = f'created {igw_id}'
            report.internet_gateway_id = igw_id

            # ── IGW_ATTACH ─────────────────────────────────────────────────────
            with timer.phase(Enum__VPC__Stack__Phase.IGW_ATTACH.value) as phase:
                # Slice 2's attach_internet_gateway swallows Resource.AlreadyAssociated
                self.ec2_client.attach_internet_gateway(igw_id, vpc_id)
                created_now['attach_vpc_for_igw'] = vpc_id                          # remember in case of rollback
                phase.detail = f'{igw_id} → {vpc_id}'

            # ── ROUTE_TABLE ────────────────────────────────────────────────────
            with timer.phase(Enum__VPC__Stack__Phase.ROUTE_TABLE.value) as phase:
                stack_rtbs = self._filter_by_tag(self.ec2_client.list_route_tables(vpc_id=vpc_id), stack_name)
                if stack_rtbs:
                    rtb_id = str(stack_rtbs[0].route_table_id)
                    phase.detail = f'reused {rtb_id}'
                    phase.status = Enum__AWS__Phase__Status.SKIPPED
                else:
                    rtb = self.ec2_client.create_route_table(
                        vpc_id=vpc_id,
                        tags  =self._stack_tags(stack_name, role='rtb'))
                    rtb_id = str(rtb.route_table_id)
                    created_now['rtb'] = rtb_id
                    phase.detail = f'created {rtb_id}'
            report.route_table_id = rtb_id

            # ── ROUTE_TO_IGW ───────────────────────────────────────────────────
            with timer.phase(Enum__VPC__Stack__Phase.ROUTE_TO_IGW.value) as phase:
                rtb_detail = self.ec2_client.describe_route_table(rtb_id)
                already = any(str(r.destination_cidr) == '0.0.0.0/0'
                              for r in (rtb_detail.routes if rtb_detail else []))
                if already:
                    phase.detail = '0.0.0.0/0 → IGW already present'
                    phase.status = Enum__AWS__Phase__Status.SKIPPED
                else:
                    self.ec2_client.create_route(rtb_id, '0.0.0.0/0',
                                                  gateway_id=igw_id)
                    created_now['route_to_igw_rtb'] = rtb_id
                    phase.detail = f'0.0.0.0/0 → {igw_id}'

            # ── SUBNETS ────────────────────────────────────────────────────────
            azs = self._resolve_azs(request.availability_zones)
            subnet_cidrs = self._derive_subnet_cidrs(request.cidr, len(azs))
            subnet_ids = []
            with timer.phase(Enum__VPC__Stack__Phase.SUBNETS.value) as phase:
                existing_subnets = self._subnets_by_index(vpc_id, stack_name)
                created_count    = 0
                reused_count     = 0
                for i, az in enumerate(azs):
                    if i in existing_subnets:
                        subnet_ids.append(existing_subnets[i])
                        reused_count += 1
                    else:
                        tags = self._stack_tags(stack_name, role='subnet')
                        tags['Subnet__Type']  = 'public'
                        tags['Subnet__Index'] = str(i)
                        sub = self.ec2_client.create_subnet(
                            vpc_id           = vpc_id,
                            cidr             = subnet_cidrs[i],
                            availability_zone= az,
                            tags             = tags)
                        subnet_ids.append(str(sub.subnet_id))
                        created_now['subnets'].append(str(sub.subnet_id))
                        created_count += 1
                phase.detail = f'created={created_count}, reused={reused_count}'
                if created_count == 0:
                    phase.status = Enum__AWS__Phase__Status.SKIPPED
            for sid in subnet_ids:
                report.subnet_ids.append(sid)

            # ── SUBNET_ATTRIBUTES ─────────────────────────────────────────────
            with timer.phase(Enum__VPC__Stack__Phase.SUBNET_ATTRIBUTES.value) as phase:
                for sid in subnet_ids:
                    self.ec2_client.modify_subnet_attribute(
                        sid, map_public_ip_on_launch=True)
                phase.detail = f'public-IP-on-launch=on for {len(subnet_ids)} subnets'

            # ── SUBNET_ASSOCIATIONS ───────────────────────────────────────────
            with timer.phase(Enum__VPC__Stack__Phase.SUBNET_ASSOCIATIONS.value) as phase:
                rtb_after = self.ec2_client.describe_route_table(rtb_id)
                already_assoc = {str(a.subnet_id) for a in (rtb_after.associations if rtb_after else [])}
                created_assocs = 0
                for sid in subnet_ids:
                    if sid in already_assoc:
                        continue
                    assoc_id = self.ec2_client.associate_route_table(rtb_id, sid)
                    if assoc_id:
                        created_now['rtb_assocs'].append(assoc_id)
                    created_assocs += 1
                phase.detail = f'created={created_assocs}, reused={len(subnet_ids) - created_assocs}'
                if created_assocs == 0:
                    phase.status = Enum__AWS__Phase__Status.SKIPPED

            # ── SECURITY_GROUP ─────────────────────────────────────────────────
            with timer.phase(Enum__VPC__Stack__Phase.SECURITY_GROUP.value) as phase:
                vpc_sgs = self.ec2_client.list_security_groups(vpc_id=vpc_id)
                tagged  = self._filter_by_tag(vpc_sgs, stack_name)
                if tagged:
                    sg_id = str(tagged[0].sg_id)
                    phase.detail = f'reused {sg_id}'
                    phase.status = Enum__AWS__Phase__Status.SKIPPED
                else:
                    # Rule 14: SG GroupName must not start with `sg-`. Use suffix.
                    sg_name = self._sg_name_for_stack(stack_name)
                    sg = self.ec2_client.create_security_group(
                        group_name  = sg_name,
                        description = f'Default SG for stack {stack_name}',
                        vpc_id      = vpc_id,
                        tags        = self._stack_tags(stack_name, role='sg'))
                    sg_id = str(sg.sg_id)
                    created_now['sg'] = sg_id
                    phase.detail = f'created {sg_id} ({sg_name})'
            report.security_group_id = sg_id

            # ── SG_INGRESS_RULES ──────────────────────────────────────────────
            with timer.phase(Enum__VPC__Stack__Phase.SG_INGRESS_RULES.value) as phase:
                created_rules = 0
                duplicate_rules = 0
                for rule in ingress_rules:
                    ok = self.ec2_client.authorize_security_group_ingress(
                        sg_id        = sg_id,
                        ip_protocol  = str(rule.protocol),
                        from_port    = int(rule.from_port),
                        to_port      = int(rule.to_port),
                        cidr_blocks  = [str(rule.cidr_block)])
                    if ok:
                        created_rules += 1
                    else:
                        duplicate_rules += 1
                phase.detail = f'created={created_rules}, duplicate={duplicate_rules}'
                if created_rules == 0:
                    phase.status = Enum__AWS__Phase__Status.SKIPPED

            # ── TAG_PROPAGATION ───────────────────────────────────────────────
            with timer.phase(Enum__VPC__Stack__Phase.TAG_PROPAGATION.value) as phase:
                ts = datetime.now(timezone.utc).isoformat()
                # Best-effort: in-memory + most boto3 clients support create_tags
                # via add_tags; the underlying EC2 client may not implement a
                # bare create_tags helper for VPCs, so we try and swallow attr-errors.
                try:
                    self.ec2_client.add_tags(vpc_id, {'Stack__Provisioned_At': ts})
                    phase.detail = f'Stack__Provisioned_At={ts}'
                except Exception as exc:                                            # noqa: BLE001 — degrade gracefully
                    phase.detail = f'tag-skip ({exc.__class__.__name__})'
                    phase.status = Enum__AWS__Phase__Status.WARN

            # ── done ──────────────────────────────────────────────────────────
            report.ok       = True
            report.phases   = timer.results or List__Schema__AWS__Phase__Result()
            report.total_ms = timer.total_ms()
            return report

        except Exception as exc:                                                    # noqa: BLE001 — orchestrator catches all
            report.ok       = False
            report.error    = f'{exc.__class__.__name__}: {exc}'
            report.phases   = timer.results or List__Schema__AWS__Phase__Result()
            report.total_ms = timer.total_ms()
            # Best-effort rollback on resources created in this run.
            self._rollback_create(report, created_now)
            return report

    def delete_stack(self, stack_name: str) -> Schema__VPC__Stack__Report:
        report = Schema__VPC__Stack__Report(operation='delete', stack_name=stack_name)
        timer  = Phase__Timer(progress_cb=self.progress_cb)

        # Resolve resources up front by tag — these are what we will tear down.
        detail = self.describe_stack(stack_name)
        if detail is None:
            report.ok       = True                                                  # nothing to do is still success
            report.phases   = timer.results or List__Schema__AWS__Phase__Result()
            report.total_ms = timer.total_ms()
            return report

        report.vpc_id              = detail.vpc_id
        report.internet_gateway_id = detail.internet_gateway_id
        report.route_table_id      = detail.route_table_id
        report.security_group_id   = detail.security_group_id
        for sid in detail.subnet_ids:
            report.subnet_ids.append(sid)

        try:
            # ── SG ─────────────────────────────────────────────────────────────
            with timer.phase(Enum__VPC__Stack__Phase.SECURITY_GROUP.value) as phase:
                if detail.security_group_id:
                    deleted = self.ec2_client.delete_security_group(detail.security_group_id)
                    phase.detail = 'deleted' if deleted else 'missing'
                    if not deleted:
                        phase.status = Enum__AWS__Phase__Status.SKIPPED
                else:
                    phase.detail = 'no SG'
                    phase.status = Enum__AWS__Phase__Status.SKIPPED

            # ── Subnets ────────────────────────────────────────────────────────
            with timer.phase(Enum__VPC__Stack__Phase.SUBNETS.value) as phase:
                count = 0
                for sid in detail.subnet_ids:
                    if self.ec2_client.delete_subnet(sid):
                        count += 1
                phase.detail = f'deleted={count}'
                if count == 0:
                    phase.status = Enum__AWS__Phase__Status.SKIPPED

            # ── Route Table ────────────────────────────────────────────────────
            with timer.phase(Enum__VPC__Stack__Phase.ROUTE_TABLE.value) as phase:
                if detail.route_table_id:
                    deleted = self.ec2_client.delete_route_table(detail.route_table_id)
                    phase.detail = 'deleted' if deleted else 'missing'
                    if not deleted:
                        phase.status = Enum__AWS__Phase__Status.SKIPPED
                else:
                    phase.detail = 'no RTB'
                    phase.status = Enum__AWS__Phase__Status.SKIPPED

            # ── IGW: detach then delete ────────────────────────────────────────
            with timer.phase(Enum__VPC__Stack__Phase.INTERNET_GATEWAY.value) as phase:
                if detail.internet_gateway_id and detail.vpc_id:
                    self.ec2_client.detach_internet_gateway(detail.internet_gateway_id,
                                                             detail.vpc_id)
                    deleted = self.ec2_client.delete_internet_gateway(detail.internet_gateway_id)
                    phase.detail = 'deleted' if deleted else 'missing'
                    if not deleted:
                        phase.status = Enum__AWS__Phase__Status.SKIPPED
                else:
                    phase.detail = 'no IGW'
                    phase.status = Enum__AWS__Phase__Status.SKIPPED

            # ── VPC ────────────────────────────────────────────────────────────
            with timer.phase(Enum__VPC__Stack__Phase.VPC.value) as phase:
                if detail.vpc_id:
                    deleted = self.ec2_client.delete_vpc(detail.vpc_id)
                    phase.detail = 'deleted' if deleted else 'missing'
                    if not deleted:
                        phase.status = Enum__AWS__Phase__Status.SKIPPED
                else:
                    phase.detail = 'no VPC'
                    phase.status = Enum__AWS__Phase__Status.SKIPPED

            report.ok       = True
            report.phases   = timer.results or List__Schema__AWS__Phase__Result()
            report.total_ms = timer.total_ms()
            return report

        except Exception as exc:                                                    # noqa: BLE001
            report.ok       = False
            report.error    = f'{exc.__class__.__name__}: {exc}'
            report.phases   = timer.results or List__Schema__AWS__Phase__Result()
            report.total_ms = timer.total_ms()
            return report

    def describe_stack(self, stack_name: str) -> Optional[Schema__VPC__Stack__Detail]:
        vpcs = self._filter_by_tag(self.ec2_client.list_vpcs(), stack_name)
        if not vpcs:
            return None
        vpc_id = str(vpcs[0].vpc_id)

        igws = self._filter_by_tag(self.ec2_client.list_internet_gateways(vpc_id=vpc_id), stack_name)
        if not igws:                                                                # IGW tag-filter may miss if list_internet_gateways doesn't accept tags client-side; fall back to attachment-vpc
            igws = list(self.ec2_client.list_internet_gateways(vpc_id=vpc_id))
            igws = self._filter_by_tag(igws, stack_name) if igws else []
        igw_id = str(igws[0].igw_id) if igws else ''

        rtbs   = self._filter_by_tag(self.ec2_client.list_route_tables(vpc_id=vpc_id), stack_name)
        rtb_id = str(rtbs[0].route_table_id) if rtbs else ''

        sgs   = self._filter_by_tag(self.ec2_client.list_security_groups(vpc_id=vpc_id), stack_name)
        sg_id = str(sgs[0].sg_id) if sgs else ''

        subnets = self._filter_by_tag(self.ec2_client.list_subnets(vpc_id=vpc_id), stack_name)
        # sort by Subnet__Index so the auto-resolve output is deterministic
        subnets_sorted = sorted(
            subnets,
            key=lambda s: int(s.tags.get('Subnet__Index', '0')) if 'Subnet__Index' in s.tags else 0)

        detail = Schema__VPC__Stack__Detail(
            stack_name          = stack_name,
            vpc_id              = vpc_id,
            internet_gateway_id = igw_id,
            route_table_id      = rtb_id,
            security_group_id   = sg_id,
        )
        for s in subnets_sorted:
            detail.subnet_ids.append(str(s.subnet_id))
        return detail

    # ── helpers ───────────────────────────────────────────────────────────────

    def _stack_tags(self, stack_name: str, role: str = '') -> dict:                # tags written on every stack resource
        tags = {'Stack': stack_name}
        if role:
            tags['Name'] = f'{stack_name}-{role}'
        return tags

    def _sg_name_for_stack(self, stack_name: str) -> str:
        # AWS rejects SG GroupName matching `sg-*` pattern (rule 14). Use suffix.
        return f'{stack_name}-sg' if not stack_name.startswith('sg-') else f'{stack_name[3:]}-sg'

    def _find_resource_by_tag(self, resources, stack_name: str):                   # first match on Stack=<stack_name>; None if no match
        matched = self._filter_by_tag(resources, stack_name)
        return matched[0] if matched else None

    def _filter_by_tag(self, resources, stack_name: str) -> list:
        matched = []
        for r in (resources or []):
            tags = getattr(r, 'tags', None) or {}
            if 'Stack' in tags and str(tags['Stack']) == stack_name:
                matched.append(r)
        return matched

    def _subnets_by_index(self, vpc_id: str, stack_name: str) -> dict:             # {int(Subnet__Index): subnet_id} for subnets tagged Stack=stack_name
        out = {}
        for s in self._filter_by_tag(self.ec2_client.list_subnets(vpc_id=vpc_id), stack_name):
            idx_raw = s.tags.get('Subnet__Index', '') if 'Subnet__Index' in s.tags else ''
            try:
                out[int(str(idx_raw))] = str(s.subnet_id)
            except (ValueError, TypeError):
                continue
        return out

    def _resolve_azs(self, requested) -> list:                                     # request.availability_zones may be empty → fallback list of two
        azs = [str(a) for a in (requested or []) if str(a).strip()]
        if azs:
            return azs
        # Best-effort: probe ec2_client.client().describe_availability_zones; if
        # the client doesn't support it (in-memory test), fall back to suffix list.
        try:
            raw = self.ec2_client.client().describe_availability_zones()
            names = [z.get('ZoneName', '') for z in raw.get('AvailabilityZones', [])
                     if z.get('ZoneName')]
            if len(names) >= 2:
                return names[:2]
        except Exception:                                                           # noqa: BLE001 — fall through to default
            pass
        # No region context → derive from session region if available, else a/b
        region = ''
        try:
            region = self.ec2_client.session.region_name or ''
        except Exception:                                                           # noqa: BLE001
            region = ''
        if region:
            return [f'{region}{suffix}' for suffix in _DEFAULT_AZS]
        return [f'eu-west-2{suffix}' for suffix in _DEFAULT_AZS]

    def _derive_subnet_cidrs(self, vpc_cidr: str, count: int) -> list:             # split vpc_cidr into `count` /20 sub-blocks (10.0.0.0/16 → /20)
        net = ipaddress.ip_network(vpc_cidr)
        # Targeting /20 from /16 yields 16 sub-blocks; from any prefix len we
        # pick the bump that gives at least `count` chunks.
        # Default: prefer +4 bits (16 subnets) for typical /16 → /20.
        bump = 4
        while net.prefixlen + bump > 32 or 2 ** bump < count:
            bump += 1
            if net.prefixlen + bump > 32:
                raise ValueError(f'Cannot derive {count} subnets from {vpc_cidr}')
        new_prefix = net.prefixlen + bump
        return [str(s) for s in list(net.subnets(new_prefix=new_prefix))[:count]]

    def _rollback_create(self, report: Schema__VPC__Stack__Report, created_now: dict) -> None:
        # Best-effort, reverse order. Never raise. Append failures to report.rollback_errors.
        def _swallow(label: str, fn):
            try:
                fn()
            except Exception as exc:                                                # noqa: BLE001
                report.rollback_errors.append(f'{label}: {exc.__class__.__name__}: {exc}')

        # rtb associations
        for assoc_id in created_now.get('rtb_assocs', []):
            _swallow(f'disassociate_route_table({assoc_id})',
                     lambda a=assoc_id: self.ec2_client.disassociate_route_table(a))
        # subnets
        for sid in reversed(created_now.get('subnets', [])):
            _swallow(f'delete_subnet({sid})',
                     lambda s=sid: self.ec2_client.delete_subnet(s))
        # route added to route table
        if created_now.get('route_to_igw_rtb'):
            rtb_id = created_now['route_to_igw_rtb']
            _swallow(f'delete_route({rtb_id}, 0.0.0.0/0)',
                     lambda: self.ec2_client.delete_route(rtb_id, '0.0.0.0/0'))
        # SG
        if created_now.get('sg'):
            sg_id = created_now['sg']
            _swallow(f'delete_security_group({sg_id})',
                     lambda: self.ec2_client.delete_security_group(sg_id))
        # rtb
        if created_now.get('rtb'):
            rtb_id = created_now['rtb']
            _swallow(f'delete_route_table({rtb_id})',
                     lambda: self.ec2_client.delete_route_table(rtb_id))
        # IGW: detach then delete (only if attach happened in this run)
        if created_now.get('attach_vpc_for_igw') and report.internet_gateway_id:
            igw_id = report.internet_gateway_id
            vpc_id = created_now['attach_vpc_for_igw']
            _swallow(f'detach_internet_gateway({igw_id}, {vpc_id})',
                     lambda: self.ec2_client.detach_internet_gateway(igw_id, vpc_id))
        if created_now.get('igw'):
            igw_id = created_now['igw']
            _swallow(f'delete_internet_gateway({igw_id})',
                     lambda: self.ec2_client.delete_internet_gateway(igw_id))
        # VPC
        if created_now.get('vpc'):
            vpc_id = created_now['vpc']
            _swallow(f'delete_vpc({vpc_id})',
                     lambda: self.ec2_client.delete_vpc(vpc_id))
