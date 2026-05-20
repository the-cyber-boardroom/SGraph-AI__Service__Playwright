# ═══════════════════════════════════════════════════════════════════════════════
# Tests — ALB__AWS__Client (via in-memory fake)
# Covers slices 1 (read), 2 (mutations), and 3 (stack provisioner).
# No mocks. No patches.
# ═══════════════════════════════════════════════════════════════════════════════

import pytest

from sgraph_ai_service_playwright__cli.aws.alb.enums.Enum__ALB__LB_State           import Enum__ALB__LB_State
from sgraph_ai_service_playwright__cli.aws.alb.enums.Enum__ALB__Target_Health       import Enum__ALB__Target_Health
from sgraph_ai_service_playwright__cli.aws.alb.service.ALB__Stack__Provisioner      import ALB__Stack__Provisioner
from sgraph_ai_service_playwright__cli.aws.alb.schemas.Schema__ALB__Stack__Request  import Schema__ALB__Stack__Request
from tests.unit.sgraph_ai_service_playwright__cli.aws.alb.service.ALB__AWS__Client__In_Memory import ALB__AWS__Client__In_Memory


def _client() -> ALB__AWS__Client__In_Memory:
    return ALB__AWS__Client__In_Memory()


class Test__ALB__AWS__Client:

    # ── Slice 1: load balancer read ───────────────────────────────────────────

    def test_1__list_load_balancers__empty(self):
        lbs = list(_client().list_load_balancers())
        assert lbs == []

    def test_2__list_load_balancers__single(self):
        c = _client()
        c.seed_load_balancer('my-alb')
        lbs = list(c.list_load_balancers())
        assert len(lbs) == 1
        assert str(lbs[0].lb_name) == 'my-alb'
        assert lbs[0].state == Enum__ALB__LB_State.ACTIVE

    def test_3__describe_load_balancer__found(self):
        c = _client()
        c.seed_load_balancer('test-lb')
        lb = c.describe_load_balancer('test-lb')
        assert lb is not None
        assert str(lb.lb_name) == 'test-lb'
        assert 'test-lb' in str(lb.lb_arn)

    def test_4__describe_load_balancer__not_found(self):
        lb = _client().describe_load_balancer('no-such-lb')
        assert lb is None

    # ── Slice 1: target group read ────────────────────────────────────────────

    def test_5__list_target_groups__empty(self):
        tgs = list(_client().list_target_groups())
        assert tgs == []

    def test_6__list_target_groups__single(self):
        c = _client()
        c.seed_target_group('my-tg')
        tgs = list(c.list_target_groups())
        assert len(tgs) == 1
        assert str(tgs[0].tg_name) == 'my-tg'
        assert int(tgs[0].port) == 8080

    def test_7__describe_target_group__found(self):
        c  = _client()
        arn = c.seed_target_group('target-group-1', vpc_id='vpc-aabb')
        tg  = c.describe_target_group(arn)
        assert tg is not None
        assert str(tg.tg_name) == 'target-group-1'
        assert str(tg.vpc_id) == 'vpc-aabb'

    # ── Slice 1: listener read ────────────────────────────────────────────────

    def test_8__list_listeners__empty(self):
        c      = _client()
        lb_arn = c.seed_load_balancer('lb-for-listeners')
        items  = list(c.list_listeners(lb_arn=lb_arn))
        assert items == []

    def test_9__list_listeners__by_lb(self):
        c           = _client()
        lb_arn      = c.seed_load_balancer('lb-with-listener')
        tg_arn      = c.seed_target_group('tg-for-listener')
        lst_arn     = c.seed_listener(lb_arn=lb_arn, tg_arn=tg_arn, port=8080)
        listeners   = list(c.list_listeners(lb_arn=lb_arn))
        assert len(listeners) == 1
        assert str(listeners[0].listener_arn) == lst_arn
        assert int(listeners[0].port) == 8080

    def test_10__describe_listener__found(self):
        c       = _client()
        lb_arn  = c.seed_load_balancer('lb-describe')
        tg_arn  = c.seed_target_group('tg-describe')
        lst_arn = c.seed_listener(lb_arn=lb_arn, tg_arn=tg_arn, port=80)
        lst     = c.describe_listener(lst_arn)
        assert lst is not None
        assert str(lst.listener_arn) == lst_arn
        assert int(lst.port) == 80
        assert str(lst.default_action.tg_arn) == tg_arn

    # ── Slice 1: target health ────────────────────────────────────────────────

    def test_11__describe_target_health__empty(self):
        c      = _client()
        tg_arn = c.seed_target_group('tg-health-empty')
        items  = list(c.describe_target_health(tg_arn))
        assert items == []

    def test_12__describe_target_health__healthy(self):
        c      = _client()
        tg_arn = c.seed_target_group('tg-health-target')
        c.seed_target_health(tg_arn, 'i-aabbccdd001122', state='healthy')
        items  = list(c.describe_target_health(tg_arn))
        assert len(items) == 1
        assert items[0].target_id == 'i-aabbccdd001122'
        assert items[0].health_status == Enum__ALB__Target_Health.HEALTHY

    # ── Slice 2: load balancer mutations ──────────────────────────────────────

    def test_13__create_load_balancer(self):
        c  = _client()
        lb = c.create_load_balancer(
            name='new-alb', subnets=['subnet-1', 'subnet-2'],
            security_groups=['sg-abc'], scheme='internet-facing',
        )
        assert lb is not None
        assert str(lb.lb_name) == 'new-alb'
        assert 'new-alb' in str(lb.lb_arn)
        all_lbs = list(c.list_load_balancers())
        assert len(all_lbs) == 1

    def test_14__delete_load_balancer(self):
        c      = _client()
        lb_arn = c.seed_load_balancer('to-delete')
        c.delete_load_balancer(lb_arn)
        assert c.describe_load_balancer('to-delete') is None

    # ── Slice 2: target group mutations ───────────────────────────────────────

    def test_15__create_target_group(self):
        c  = _client()
        tg = c.create_target_group(
            name='new-tg', vpc_id='vpc-abc', port=8080,
            health_check_path='/info/health',
        )
        assert tg is not None
        assert str(tg.tg_name) == 'new-tg'
        assert int(tg.port) == 8080
        assert str(tg.health_check_path) == '/info/health'

    def test_16__register_targets(self):
        c      = _client()
        tg_arn = c.seed_target_group('reg-tg')
        c.register_targets(tg_arn=tg_arn, targets=[{'Id': 'i-001', 'Port': 8080}])
        health = list(c.describe_target_health(tg_arn))
        assert len(health) == 1
        assert health[0].target_id == 'i-001'

    # ── Slice 2: listener mutations ───────────────────────────────────────────

    def test_17__create_listener(self):
        c        = _client()
        lb_arn   = c.seed_load_balancer('lb-listener')
        tg_arn   = c.seed_target_group('tg-listener')
        listener = c.create_listener(lb_arn=lb_arn, tg_arn=tg_arn, port=80)
        assert listener is not None
        assert int(listener.port) == 80
        assert str(listener.lb_arn) == lb_arn
        assert str(listener.default_action.tg_arn) == tg_arn
        listeners = list(c.list_listeners(lb_arn=lb_arn))
        assert len(listeners) == 1

    # ── Slice 3: stack provisioner ────────────────────────────────────────────

    def test_18__stack_provisioner__create_and_describe(self):
        c           = _client()
        provisioner = ALB__Stack__Provisioner(alb_client=c)
        request     = Schema__ALB__Stack__Request(
            stack_name  = 'test-stack',
            vpc_id      = 'vpc-test',
            subnet_ids  = ['subnet-a', 'subnet-b'],
            lb_port     = 80,
            target_port = 8080,
        )
        report = provisioner.create_stack(request)
        assert report.ok is True
        assert report.lb_arn != ''
        assert report.tg_arn != ''
        assert report.listener_arn != ''

        detail = provisioner.describe_stack('test-stack')
        assert detail is not None
        assert detail.stack_name == 'test-stack'
        assert detail.lb_arn == report.lb_arn
        assert detail.tg_arn == report.tg_arn
        assert detail.listener_arn == report.listener_arn

    def test_19__stack_provisioner__idempotent_rerun(self):
        c           = _client()
        provisioner = ALB__Stack__Provisioner(alb_client=c)
        request     = Schema__ALB__Stack__Request(
            stack_name  = 'idempotent-stack',
            vpc_id      = 'vpc-idm',
            subnet_ids  = ['subnet-x', 'subnet-y'],
            lb_port     = 80,
            target_port = 8080,
        )
        report1 = provisioner.create_stack(request)
        assert report1.ok is True

        report2 = provisioner.create_stack(request)
        assert report2.ok is True
        assert report2.lb_arn == report1.lb_arn      # same LB reused
        assert report2.tg_arn == report1.tg_arn      # same TG reused
        assert report2.listener_arn == report1.listener_arn

        lbs = list(c.list_load_balancers())
        assert len(lbs) == 1                          # no duplicate LBs

    def test_20__stack_provisioner__delete(self):
        c           = _client()
        provisioner = ALB__Stack__Provisioner(alb_client=c)
        request     = Schema__ALB__Stack__Request(
            stack_name  = 'delete-stack',
            vpc_id      = 'vpc-del',
            subnet_ids  = ['subnet-1', 'subnet-2'],
            lb_port     = 80,
            target_port = 8080,
        )
        report_create = provisioner.create_stack(request)
        assert report_create.ok is True

        report_delete = provisioner.delete_stack('delete-stack')
        assert report_delete.ok is True

        detail = provisioner.describe_stack('delete-stack')
        assert detail is None

        lbs = list(c.list_load_balancers())
        assert lbs == []

    def test_21__lb_name_collision_avoided(self):
        # Two long stack names that share a 28-char prefix must NOT collapse
        # to the same LB name once we shrink them to fit AWS's 32-char limit.
        from sgraph_ai_service_playwright__cli.aws.alb.service.ALB__Stack__Provisioner import _lb_name, _tg_name, _shrink_name

        stack_a = 'super-long-stack-name-aaaaaa-one'                                  # 32 chars, shared 28-char prefix
        stack_b = 'super-long-stack-name-aaaaaa-two'                                  # 32 chars, shared 28-char prefix
        assert stack_a[:28] == stack_b[:28]

        name_a = _lb_name(stack_a)
        name_b = _lb_name(stack_b)
        assert name_a != name_b                                                       # collision avoided
        assert len(name_a) <= 32
        assert len(name_b) <= 32
        assert name_a.endswith('-alb')
        assert name_b.endswith('-alb')

        # Same property for the TG name suffix.
        tg_a = _tg_name(stack_a)
        tg_b = _tg_name(stack_b)
        assert tg_a != tg_b
        assert tg_a.endswith('-tg')
        assert tg_b.endswith('-tg')

        # Short stacks should pass through unchanged (no hashing).
        assert _lb_name('short') == 'short-alb'
        assert _shrink_name('short', '-tg') == 'short-tg'
