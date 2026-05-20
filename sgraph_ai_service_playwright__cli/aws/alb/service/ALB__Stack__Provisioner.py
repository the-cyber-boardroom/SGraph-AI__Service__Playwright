# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/alb — ALB__Stack__Provisioner
# Orchestrates ALB CRUD primitives into a full ALB stack:
#   2 security groups → load balancer → target group → listener.
# Idempotent: re-running with the same stack_name finds resources by name
#   convention and SKIPs phases that already exist.
# Name convention:
#   LB:          {stack_name}-alb   (max 32 chars; truncated if needed)
#   TG:          {stack_name}-tg
#   alb SG:      {stack_name}-alb-sg
#   target SG:   {stack_name}-target-sg
# Best-effort rollback on first phase ERROR.
# ═══════════════════════════════════════════════════════════════════════════════

import hashlib
from typing import Optional

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws._shared.Phase__Timer                                 import Phase__Timer
from sgraph_ai_service_playwright__cli.aws._shared.enums.Enum__AWS__Phase__Status               import Enum__AWS__Phase__Status
from sgraph_ai_service_playwright__cli.aws.alb.primitives.Safe_Str__ALB__LB_Arn                 import Safe_Str__ALB__LB_Arn
from sgraph_ai_service_playwright__cli.aws.alb.primitives.Safe_Str__ALB__TG_Arn                 import Safe_Str__ALB__TG_Arn
from sgraph_ai_service_playwright__cli.aws.alb.primitives.Safe_Str__ALB__Listener_Arn           import Safe_Str__ALB__Listener_Arn
from sgraph_ai_service_playwright__cli.aws.alb.schemas.Schema__ALB__Stack__Detail               import Schema__ALB__Stack__Detail
from sgraph_ai_service_playwright__cli.aws.alb.schemas.Schema__ALB__Stack__Report               import Schema__ALB__Stack__Report
from sgraph_ai_service_playwright__cli.aws.alb.schemas.Schema__ALB__Stack__Request              import Schema__ALB__Stack__Request


_ALB_SUFFIX    = '-alb'
_TG_SUFFIX     = '-tg'
_ALB_SG_SUFFIX = '-alb-sg'
_TGT_SG_SUFFIX = '-target-sg'
_MAX_LB_NAME   = 32                                                                # AWS ALB name length limit


def _shrink_name(stack: str, suffix: str) -> str:                                  # collision-safe truncation; hash-suffix when stack+suffix exceeds the 32-char AWS limit
    max_total = _MAX_LB_NAME
    if len(stack + suffix) <= max_total:
        return stack + suffix
    # Hash the full stack name into 6 hex chars; reserve room for the hash + suffix.
    digest   = hashlib.sha1(stack.encode('utf-8')).hexdigest()[:6]
    reserved = len(suffix) + 1 + len(digest)                                       # 1 for '-' separator
    head_len = max_total - reserved
    if head_len < 1:
        raise ValueError(f'stack name {stack!r} too long even with hash suffix')
    return f'{stack[:head_len]}-{digest}{suffix}'


def _lb_name(stack: str) -> str:
    return _shrink_name(stack, _ALB_SUFFIX)


def _tg_name(stack: str) -> str:
    return _shrink_name(stack, _TG_SUFFIX)


class ALB__Stack__Provisioner(Type_Safe):
    alb_client  : object = None                                                    # ALB__AWS__Client — injected
    ec2_client  : object = None                                                    # EC2__AWS__Client — injected (for SG creation)
    progress_cb : object = None                                                    # callable(phase_name, status, detail='') or None

    # ── public ────────────────────────────────────────────────────────────────

    def create_stack(self, request: Schema__ALB__Stack__Request) -> Schema__ALB__Stack__Report:
        stack_name = request.stack_name
        report     = Schema__ALB__Stack__Report(operation='create', stack_name=stack_name)
        timer      = Phase__Timer(progress_cb=self.progress_cb)
        created    = {'alb_sg': '', 'target_sg': '', 'lb': '', 'tg': '', 'listener': ''}

        try:
            # ── SECURITY_GROUPS ───────────────────────────────────────────────
            with timer.phase('SECURITY_GROUPS') as phase:
                alb_sg_id, target_sg_id = self._ensure_security_groups(
                    stack_name    = stack_name,
                    vpc_id        = request.vpc_id,
                    target_port   = request.target_port,
                    created       = created,
                )
                report.alb_sg_id    = alb_sg_id
                report.target_sg_id = target_sg_id
                phase.detail = f'alb-sg={alb_sg_id} target-sg={target_sg_id}'

            # ── LOAD_BALANCER ─────────────────────────────────────────────────
            with timer.phase('LOAD_BALANCER') as phase:
                lb_name_str = _lb_name(stack_name)
                existing_lb = self.alb_client.describe_load_balancer(lb_name_str)
                if existing_lb is not None:
                    lb_arn     = str(existing_lb.lb_arn)
                    lb_dns     = existing_lb.dns_name
                    phase.detail = f'reused {lb_arn}'
                    phase.status = Enum__AWS__Phase__Status.SKIPPED
                else:
                    tags    = {str(k): str(v) for k, v in dict(request.tags).items()}
                    tags['Stack'] = stack_name
                    lb      = self.alb_client.create_load_balancer(
                        name            = lb_name_str,
                        subnets         = [str(s) for s in request.subnet_ids],
                        security_groups = [alb_sg_id] if alb_sg_id else [],
                        scheme          = 'internet-facing',
                        tags            = tags,
                    )
                    lb_arn       = str(lb.lb_arn)
                    lb_dns       = lb.dns_name
                    created['lb'] = lb_arn
                    phase.detail = f'created {lb_arn}'
                report.lb_arn     = lb_arn
                report.lb_dns_name = lb_dns

            # ── TARGET_GROUP ──────────────────────────────────────────────────
            with timer.phase('TARGET_GROUP') as phase:
                tg_name_str  = _tg_name(stack_name)
                existing_tgs = self.alb_client.list_target_groups()
                existing_tg  = None
                for tg in existing_tgs:
                    if str(tg.tg_name) == tg_name_str:
                        existing_tg = tg
                        break
                if existing_tg is not None:
                    tg_arn       = str(existing_tg.tg_arn)
                    phase.detail = f'reused {tg_arn}'
                    phase.status = Enum__AWS__Phase__Status.SKIPPED
                else:
                    tags    = {str(k): str(v) for k, v in dict(request.tags).items()}
                    tags['Stack'] = stack_name
                    tg      = self.alb_client.create_target_group(
                        name                  = tg_name_str,
                        vpc_id                = request.vpc_id,
                        protocol              = 'HTTP',
                        port                  = request.target_port,
                        target_type           = str(request.target_type),
                        health_check_protocol = 'HTTP',
                        health_check_port     = str(request.target_port),
                        health_check_path     = request.health_check_path,
                        tags                  = tags,
                    )
                    tg_arn       = str(tg.tg_arn)
                    created['tg'] = tg_arn
                    phase.detail = f'created {tg_arn}'
                report.tg_arn = tg_arn

            # ── LISTENER ──────────────────────────────────────────────────────
            with timer.phase('LISTENER') as phase:
                existing_listeners = self.alb_client.list_listeners(lb_arn=lb_arn)
                if existing_listeners and len(existing_listeners) > 0:
                    listener_arn = str(existing_listeners[0].listener_arn)
                    phase.detail = f'reused {listener_arn}'
                    phase.status = Enum__AWS__Phase__Status.SKIPPED
                else:
                    listener      = self.alb_client.create_listener(
                        lb_arn   = lb_arn,
                        tg_arn   = tg_arn,
                        protocol = 'HTTP',
                        port     = request.lb_port,
                    )
                    listener_arn        = str(listener.listener_arn)
                    created['listener'] = listener_arn
                    phase.detail        = f'created {listener_arn}'
                report.listener_arn = listener_arn

            report.ok       = True
            report.phases   = timer.results
            report.total_ms = timer.total_ms()

        except Exception as exc:                                                   # best-effort rollback in reverse
            report.error   = str(exc)
            report.phases  = timer.results
            report.total_ms = timer.total_ms()
            for err in self._rollback(created):
                report.rollback_errors.append(err)

        return report

    def delete_stack(self, stack_name: str) -> Schema__ALB__Stack__Report:
        report  = Schema__ALB__Stack__Report(operation='delete', stack_name=stack_name)
        timer   = Phase__Timer(progress_cb=self.progress_cb)

        try:
            # ── LISTENER ──────────────────────────────────────────────────────
            with timer.phase('LISTENER') as phase:
                lb_name_str = _lb_name(stack_name)
                try:
                    existing_lb = self.alb_client.describe_load_balancer(lb_name_str)
                except Exception as exc:                                             # noqa: BLE001 — collect, continue
                    report.rollback_errors.append(f'describe_load_balancer({lb_name_str}): {exc.__class__.__name__}: {exc}')
                    existing_lb = None
                if existing_lb is None:
                    phase.detail = 'no lb found — skip'
                    phase.status = Enum__AWS__Phase__Status.SKIPPED
                else:
                    try:
                        listeners = self.alb_client.list_listeners(lb_arn=str(existing_lb.lb_arn))
                    except Exception as exc:                                         # noqa: BLE001
                        report.rollback_errors.append(f'list_listeners({existing_lb.lb_arn}): {exc.__class__.__name__}: {exc}')
                        listeners = []
                    attempted    = 0
                    deleted_okay = 0
                    for listener in listeners:
                        attempted += 1
                        try:
                            self.alb_client.delete_listener(str(listener.listener_arn))
                            deleted_okay += 1
                        except Exception as exc:                                     # noqa: BLE001
                            report.rollback_errors.append(f'delete_listener({listener.listener_arn}): {exc.__class__.__name__}: {exc}')
                    if attempted == 0:
                        phase.detail = 'no listeners — skip'
                        phase.status = Enum__AWS__Phase__Status.SKIPPED
                    else:
                        phase.detail = f'deleted {deleted_okay}/{attempted} listener(s)'
                        if deleted_okay == 0:
                            phase.status = Enum__AWS__Phase__Status.ERROR

            # ── TARGET_GROUP ──────────────────────────────────────────────────
            with timer.phase('TARGET_GROUP') as phase:
                tg_name_str = _tg_name(stack_name)
                try:
                    all_tgs = self.alb_client.list_target_groups()
                except Exception as exc:                                             # noqa: BLE001
                    report.rollback_errors.append(f'list_target_groups: {exc.__class__.__name__}: {exc}')
                    all_tgs = []
                attempted    = 0
                deleted_okay = 0
                for tg in all_tgs:
                    if str(tg.tg_name) == tg_name_str:
                        attempted += 1
                        try:
                            self.alb_client.delete_target_group(str(tg.tg_arn))
                            deleted_okay += 1
                        except Exception as exc:                                     # noqa: BLE001
                            report.rollback_errors.append(f'delete_target_group({tg.tg_arn}): {exc.__class__.__name__}: {exc}')
                if attempted == 0:
                    phase.detail = 'no target groups — skip'
                    phase.status = Enum__AWS__Phase__Status.SKIPPED
                else:
                    phase.detail = f'deleted {deleted_okay}/{attempted} target group(s)'
                    if deleted_okay == 0:
                        phase.status = Enum__AWS__Phase__Status.ERROR

            # ── LOAD_BALANCER ─────────────────────────────────────────────────
            with timer.phase('LOAD_BALANCER') as phase:
                lb_name_str = _lb_name(stack_name)
                try:
                    existing_lb = self.alb_client.describe_load_balancer(lb_name_str)
                except Exception as exc:                                             # noqa: BLE001
                    report.rollback_errors.append(f'describe_load_balancer({lb_name_str}): {exc.__class__.__name__}: {exc}')
                    existing_lb = None
                if existing_lb is None:
                    phase.detail = 'not found — skip'
                    phase.status = Enum__AWS__Phase__Status.SKIPPED
                else:
                    try:
                        self.alb_client.delete_load_balancer(str(existing_lb.lb_arn))
                        phase.detail = f'deleted {existing_lb.lb_arn}'
                    except Exception as exc:                                         # noqa: BLE001
                        report.rollback_errors.append(f'delete_load_balancer({existing_lb.lb_arn}): {exc.__class__.__name__}: {exc}')
                        phase.detail = f'failed to delete {existing_lb.lb_arn}'
                        phase.status = Enum__AWS__Phase__Status.ERROR

            # ── SECURITY_GROUPS ───────────────────────────────────────────────
            with timer.phase('SECURITY_GROUPS') as phase:
                attempted    = 0
                deleted_okay = 0
                if self.ec2_client is not None:
                    for suffix in (_ALB_SG_SUFFIX, _TGT_SG_SUFFIX):
                        sg_name = stack_name + suffix
                        try:
                            existing = self.ec2_client.describe_security_group(sg_name)
                        except Exception as exc:                                     # noqa: BLE001
                            report.rollback_errors.append(f'describe_security_group({sg_name}): {exc.__class__.__name__}: {exc}')
                            continue
                        if existing is None:
                            continue
                        attempted += 1
                        try:
                            self.ec2_client.delete_security_group(str(existing.sg_id))
                            deleted_okay += 1
                        except Exception as exc:                                     # noqa: BLE001
                            report.rollback_errors.append(f'delete_security_group({existing.sg_id}): {exc.__class__.__name__}: {exc}')
                if attempted == 0:
                    phase.detail = 'no security groups — skip'
                    phase.status = Enum__AWS__Phase__Status.SKIPPED
                else:
                    phase.detail = f'deleted {deleted_okay}/{attempted} security group(s)'
                    if deleted_okay == 0:
                        phase.status = Enum__AWS__Phase__Status.ERROR

            # ok=True if destroy ran end-to-end (rollback_errors may still be populated)
            report.ok       = True
            report.phases   = timer.results
            report.total_ms = timer.total_ms()

        except Exception as exc:                                                     # noqa: BLE001 — only setup failures land here
            report.error    = str(exc)
            report.phases   = timer.results
            report.total_ms = timer.total_ms()

        return report

    def describe_stack(self, stack_name: str) -> Optional[Schema__ALB__Stack__Detail]:
        lb_name_str = _lb_name(stack_name)
        existing_lb = self.alb_client.describe_load_balancer(lb_name_str)
        if existing_lb is None:
            return None
        lb_arn = str(existing_lb.lb_arn)
        detail = Schema__ALB__Stack__Detail(
            stack_name  = stack_name,
            lb_arn      = Safe_Str__ALB__LB_Arn(lb_arn),
            lb_dns_name = existing_lb.dns_name,
        )
        tg_name_str = _tg_name(stack_name)
        all_tgs     = self.alb_client.list_target_groups()
        for tg in all_tgs:
            if str(tg.tg_name) == tg_name_str:
                detail.tg_arn = Safe_Str__ALB__TG_Arn(str(tg.tg_arn))
                break
        listeners = self.alb_client.list_listeners(lb_arn=lb_arn)
        if listeners and len(listeners) > 0:
            detail.listener_arn = Safe_Str__ALB__Listener_Arn(str(listeners[0].listener_arn))
        if self.ec2_client is not None:
            alb_sg = self.ec2_client.describe_security_group(stack_name + _ALB_SG_SUFFIX)
            if alb_sg is not None:
                detail.alb_sg_id = str(alb_sg.sg_id)
            target_sg = self.ec2_client.describe_security_group(stack_name + _TGT_SG_SUFFIX)
            if target_sg is not None:
                detail.target_sg_id = str(target_sg.sg_id)
        return detail

    # ── internal ──────────────────────────────────────────────────────────────

    def _ensure_security_groups(self, stack_name: str, vpc_id: str,
                                  target_port: int,
                                  created: dict) -> tuple:
        if self.ec2_client is None:
            return '', ''

        alb_sg_name = stack_name + _ALB_SG_SUFFIX
        tgt_sg_name = stack_name + _TGT_SG_SUFFIX

        # find-or-create ALB security group
        alb_sg = self.ec2_client.describe_security_group(alb_sg_name, vpc_id=vpc_id)
        if alb_sg is None:
            alb_sg = self.ec2_client.create_security_group(
                group_name  = alb_sg_name,
                description = f'ALB SG for stack {stack_name}',
                vpc_id      = vpc_id,
                tags        = {'Stack': stack_name, 'ALB-Role': 'alb-sg'},
            )
            created['alb_sg'] = str(alb_sg.sg_id)
            # ingress 80 and 443 from 0.0.0.0/0
            self.ec2_client.authorize_security_group_ingress(
                sg_id=str(alb_sg.sg_id), ip_protocol='tcp',
                from_port=80, to_port=80, cidr_blocks=['0.0.0.0/0'])
            self.ec2_client.authorize_security_group_ingress(
                sg_id=str(alb_sg.sg_id), ip_protocol='tcp',
                from_port=443, to_port=443, cidr_blocks=['0.0.0.0/0'])
        alb_sg_id = str(alb_sg.sg_id)

        # find-or-create target security group
        target_sg = self.ec2_client.describe_security_group(tgt_sg_name, vpc_id=vpc_id)
        if target_sg is None:
            target_sg = self.ec2_client.create_security_group(
                group_name  = tgt_sg_name,
                description = f'Target SG for stack {stack_name}',
                vpc_id      = vpc_id,
                tags        = {'Stack': stack_name, 'ALB-Role': 'target-sg'},
            )
            created['target_sg'] = str(target_sg.sg_id)
            # ingress target_port from alb-sg
            self.ec2_client.authorize_security_group_ingress(
                sg_id=str(target_sg.sg_id), ip_protocol='tcp',
                from_port=target_port, to_port=target_port,
                source_sg_ids=[alb_sg_id])
        target_sg_id = str(target_sg.sg_id)

        return alb_sg_id, target_sg_id

    def _rollback(self, created: dict) -> list:
        errors = []
        for listener_arn in ([created['listener']] if created.get('listener') else []):
            try:
                self.alb_client.delete_listener(listener_arn)
            except Exception as exc:
                errors.append(f'rollback delete listener {listener_arn}: {exc}')
        for tg_arn in ([created['tg']] if created.get('tg') else []):
            try:
                self.alb_client.delete_target_group(tg_arn)
            except Exception as exc:
                errors.append(f'rollback delete target group {tg_arn}: {exc}')
        for lb_arn in ([created['lb']] if created.get('lb') else []):
            try:
                self.alb_client.delete_load_balancer(lb_arn)
            except Exception as exc:
                errors.append(f'rollback delete lb {lb_arn}: {exc}')
        if self.ec2_client is not None:
            for sg_id in ([created['target_sg']] if created.get('target_sg') else []):
                try:
                    self.ec2_client.delete_security_group(sg_id)
                except Exception as exc:
                    errors.append(f'rollback delete target-sg {sg_id}: {exc}')
            for sg_id in ([created['alb_sg']] if created.get('alb_sg') else []):
                try:
                    self.ec2_client.delete_security_group(sg_id)
                except Exception as exc:
                    errors.append(f'rollback delete alb-sg {sg_id}: {exc}')
        return errors
