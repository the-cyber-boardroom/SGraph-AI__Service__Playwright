# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/alb — ALB__Perf_Test__Runner
# 6-phase orchestrator: PROVISION → WAIT_LB_ACTIVE → REGISTER_TARGET →
#   WAIT_HEALTHY → HTTP_PROBE → TEARDOWN.
# TEARDOWN runs even on phase failure unless request.keep is True.
# All collaborators are injected so tests can swap fakes — no mocks, no patches.
# ═══════════════════════════════════════════════════════════════════════════════

import secrets
import time

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws._shared.Phase__Timer                                   import Phase__Timer
from sgraph_ai_service_playwright__cli.aws._shared.collections.List__Schema__AWS__Phase__Result   import List__Schema__AWS__Phase__Result
from sgraph_ai_service_playwright__cli.aws._shared.enums.Enum__AWS__Phase__Status                 import Enum__AWS__Phase__Status
from sgraph_ai_service_playwright__cli.aws.alb.enums.Enum__ALB__Perf_Test__Phase                  import Enum__ALB__Perf_Test__Phase
from sgraph_ai_service_playwright__cli.aws.alb.enums.Enum__ALB__Target_Type                       import Enum__ALB__Target_Type
from sgraph_ai_service_playwright__cli.aws.alb.schemas.Schema__ALB__Perf_Test__Report             import Schema__ALB__Perf_Test__Report
from sgraph_ai_service_playwright__cli.aws.alb.schemas.Schema__ALB__Perf_Test__Request            import Schema__ALB__Perf_Test__Request
from sgraph_ai_service_playwright__cli.aws.alb.schemas.Schema__ALB__Stack__Request                import Schema__ALB__Stack__Request
from sgraph_ai_service_playwright__cli.aws.alb.service.ALB__HTTP__Probe                           import ALB__HTTP__Probe
from sgraph_ai_service_playwright__cli.aws.alb.service.ALB__LB__Wait__Active                      import ALB__LB__Wait__Active
from sgraph_ai_service_playwright__cli.aws.alb.service.ALB__Stack__Provisioner                    import ALB__Stack__Provisioner
from sgraph_ai_service_playwright__cli.aws.alb.service.ALB__Target__Wait__Healthy                 import ALB__Target__Wait__Healthy


class ALB__Perf_Test__Runner(Type_Safe):
    alb_client    : object = None                                                  # ALB__AWS__Client — injected
    ec2_client    : object = None                                                  # EC2__AWS__Client — injected
    http_probe    : object = None                                                  # ALB__HTTP__Probe — injected (fakeable)
    lb_waiter     : object = None                                                  # ALB__LB__Wait__Active — injected (fakeable)
    target_waiter : object = None                                                  # ALB__Target__Wait__Healthy — injected (fakeable)
    progress_cb   : object = None                                                  # callable(name, status, detail='')
    sleep_fn      : object = None                                                  # for tests: defaults to time.sleep

    def setup(self) -> None:                                                       # idempotent — populate any None field with a default
        if self.sleep_fn is None:
            self.sleep_fn = time.sleep
        if self.http_probe is None:
            self.http_probe = ALB__HTTP__Probe()
        if self.lb_waiter is None:
            self.lb_waiter = ALB__LB__Wait__Active(alb_client=self.alb_client)
        if self.target_waiter is None:
            self.target_waiter = ALB__Target__Wait__Healthy(alb_client=self.alb_client)

    # ── public ────────────────────────────────────────────────────────────────

    def run(self, request: Schema__ALB__Perf_Test__Request) -> Schema__ALB__Perf_Test__Report:
        self.setup()
        stack_name = str(request.name) or f'perf-{secrets.token_hex(4)}'
        report     = Schema__ALB__Perf_Test__Report(stack_name=stack_name)
        timer      = Phase__Timer(progress_cb=self.progress_cb)
        provisioner = ALB__Stack__Provisioner(alb_client  = self.alb_client,
                                              ec2_client  = self.ec2_client,
                                              progress_cb = None)
        # ── orchestrate phases 1-5, then ALWAYS run TEARDOWN (unless keep) ──
        phase_failure = False
        try:
            # Phase 1 PROVISION
            with timer.phase(Enum__ALB__Perf_Test__Phase.PROVISION.value) as phase:
                stack_req = Schema__ALB__Stack__Request(
                    stack_name        = stack_name,
                    vpc_id            = str(request.vpc_id),
                    target_type       = Enum__ALB__Target_Type.IP,
                    lb_port           = 80,
                    target_port       = int(request.target_port),
                    health_check_path = str(request.http_path),
                )
                for sid in request.subnet_ids:
                    stack_req.subnet_ids.append(str(sid))
                stack_report = provisioner.create_stack(stack_req)
                report.lb_arn      = str(stack_report.lb_arn)
                report.tg_arn      = str(stack_report.tg_arn)
                report.lb_dns_name = str(stack_report.lb_dns_name)
                if not stack_report.ok:
                    phase.detail = f'provision failed: {stack_report.error}'
                    raise RuntimeError(f'PROVISION failed: {stack_report.error}')
                phase.detail = f'lb={report.lb_arn} tg={report.tg_arn}'

            # Phase 2 WAIT_LB_ACTIVE
            with timer.phase(Enum__ALB__Perf_Test__Phase.WAIT_LB_ACTIVE.value) as phase:
                ok, attempts, last_state = self.lb_waiter.wait(report.lb_arn,
                                                                int(request.lb_active_timeout))
                phase.detail = f'attempts={attempts} state={last_state}'
                if not ok:
                    raise RuntimeError(f'WAIT_LB_ACTIVE timeout after {attempts} attempts (state={last_state})')

            # Phase 3 REGISTER_TARGET
            with timer.phase(Enum__ALB__Perf_Test__Phase.REGISTER_TARGET.value) as phase:
                self.alb_client.register_targets(
                    report.tg_arn,
                    [{'Id': str(request.target_ip), 'Port': int(request.target_port)}],
                )
                report.target_registered = True
                phase.detail = f'target={request.target_ip}:{request.target_port}'

            # Phase 4 WAIT_HEALTHY
            with timer.phase(Enum__ALB__Perf_Test__Phase.WAIT_HEALTHY.value) as phase:
                ok, attempts, last_state = self.target_waiter.wait(
                    report.tg_arn, str(request.target_ip), int(request.healthy_timeout))
                phase.detail = f'attempts={attempts} state={last_state}'
                if not ok:
                    raise RuntimeError(f'WAIT_HEALTHY timeout after {attempts} attempts (state={last_state})')

            # Phase 5 HTTP_PROBE
            with timer.phase(Enum__ALB__Perf_Test__Phase.HTTP_PROBE.value) as phase:
                path     = str(request.http_path)
                if not path.startswith('/'):
                    path = '/' + path
                url      = f'http://{report.lb_dns_name}{path}'
                results  = []
                for _ in range(max(int(request.http_probes), 1)):
                    probe_result = self.http_probe.probe(url)
                    report.probes.append(probe_result)
                    results.append(probe_result)
                ok_count = sum(1 for r in results if int(r.status_code) == int(request.expected_status))
                phase.detail = f'{ok_count}/{len(results)} probes returned {request.expected_status}'
                if ok_count != len(results):
                    raise RuntimeError(f'HTTP_PROBE expected {request.expected_status}, got mixed: '
                                       + ','.join(str(r.status_code) for r in results))

        except Exception as exc:                                                   # noqa: BLE001 — orchestrator catches all phase failures
            phase_failure = True
            report.error  = f'{exc.__class__.__name__}: {exc}'

        # Phase 6 TEARDOWN — runs even on failure unless keep=True
        try:
            with timer.phase(Enum__ALB__Perf_Test__Phase.TEARDOWN.value) as phase:
                if bool(request.keep):
                    phase.detail = 'keep=True — stack left in place'
                    phase.status = Enum__AWS__Phase__Status.SKIPPED
                else:
                    teardown_report = provisioner.delete_stack(stack_name)
                    for err in (teardown_report.rollback_errors or []):
                        report.rollback_errors.append(str(err))
                    if teardown_report.ok:
                        phase.detail = 'destroyed'
                    else:
                        phase.detail = f'partial: {teardown_report.error}'
                        phase.status = Enum__AWS__Phase__Status.WARN
        except Exception as exc:                                                   # noqa: BLE001 — never raise from teardown
            report.rollback_errors.append(f'teardown exception: {exc.__class__.__name__}: {exc}')

        report.phases   = timer.results or List__Schema__AWS__Phase__Result()
        report.total_ms = timer.total_ms()
        report.ok       = (not phase_failure)
        return report
