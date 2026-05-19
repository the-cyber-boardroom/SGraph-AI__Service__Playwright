# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute_specs vault_app/fargate — Vault_App__Fargate__Starter
# Fast-path orchestrator: RESOLVE_CONFIG → RUN_TASK → WAIT_RUNNING →
# RESOLVE_ENI → WAIT_HEALTH.  All AWS calls via injected clients.
# DNS_UPSERT is a no-op stub in v1 (with_aws_dns not implemented).
# progress_cb fires (name, status, detail='') on phase enter+exit.
# ═══════════════════════════════════════════════════════════════════════════════

import time as _time
from datetime import datetime, timezone

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute.platforms.ec2.networking.Stack__Name__Generator                    import Stack__Name__Generator
from sg_compute_specs.vault_app.fargate.enums.Enum__VAF__Start__Phase              import Enum__VAF__Start__Phase
from sg_compute_specs.vault_app.fargate.schemas.Schema__VAF__Start__Report         import Schema__VAF__Start__Report
from sg_compute_specs.vault_app.fargate.schemas.Schema__VAF__Start__Request        import Schema__VAF__Start__Request
from sg_compute_specs.vault_app.fargate.schemas.Schema__VAF__Timings__Record       import Schema__VAF__Timings__Record
from sg_compute_specs.vault_app.fargate.service.Phase__Timer                       import Phase__Timer
from sg_compute_specs.vault_app.fargate.service.Vault_App__Fargate__Health         import Vault_App__Fargate__Health
from sg_compute_specs.vault_app.fargate.service.Vault_App__Fargate__Slug__Resolver import Vault_App__Fargate__Slug__Resolver
from sg_compute_specs.vault_app.fargate.service.Vault_App__Fargate__Spec           import Vault_App__Fargate__Spec
from sg_compute_specs.vault_app.fargate.service.Vault_App__Fargate__Tags__Reader   import Vault_App__Fargate__Tags__Reader
from sg_compute_specs.vault_app.fargate.service.Vault_App__Fargate__Timings__Store import Vault_App__Fargate__Timings__Store


class Vault_App__Fargate__Starter(Type_Safe):
    spec           : Vault_App__Fargate__Spec           = None
    tags_reader    : Vault_App__Fargate__Tags__Reader   = None
    health         : Vault_App__Fargate__Health         = None
    slug_resolver  : Vault_App__Fargate__Slug__Resolver = None
    timings_store  : Vault_App__Fargate__Timings__Store = None

    fargate_client : object = None                                                # Fargate__AWS__Client — injected
    ec2_client     : object = None                                                # EC2__AWS__Client — injected

    progress_cb    : object = None                                                # callable(name, status, detail='') or None

    def setup(self) -> None:                                                      # idempotent; fills None fields with real defaults
        if not self.spec:
            self.spec          = Vault_App__Fargate__Spec()
        if not self.health:
            self.health        = Vault_App__Fargate__Health()
        if not self.tags_reader:
            self.tags_reader   = Vault_App__Fargate__Tags__Reader(fargate_client=self.fargate_client)
        if not self.slug_resolver:
            self.slug_resolver = Vault_App__Fargate__Slug__Resolver(fargate_client=self.fargate_client)
        if not self.timings_store:
            self.timings_store = Vault_App__Fargate__Timings__Store()

    # ── main entry point ──────────────────────────────────────────────────────

    def start(self, request: Schema__VAF__Start__Request) -> Schema__VAF__Start__Report:
        self.setup()
        timer  = Phase__Timer(progress_cb=self.progress_cb)
        report = Schema__VAF__Start__Report(
            executed_at = datetime.now(timezone.utc).isoformat()
        )

        try:
            # ── Phase 1: RESOLVE_CONFIG ───────────────────────────────────────
            # Two AWS describes in parallel — ~50ms vs ~100ms sequential.
            cluster_cfg = None
            with timer.phase(Enum__VAF__Start__Phase.RESOLVE_CONFIG.value) as result:
                from concurrent.futures import ThreadPoolExecutor
                with ThreadPoolExecutor(max_workers=2) as ex:
                    fut_cfg = ex.submit(self.tags_reader.read, request.cluster_name)
                    fut_td  = ex.submit(self.fargate_client.describe_task_definition,
                                        self.spec.default_task_def_family)
                    cluster_cfg = fut_cfg.result()
                    fut_td.result()                                          # validate task-def exists; result not used in v1
                result.detail = f'cluster={cluster_cfg.cluster_name}'

            # ── Phase 2: RUN_TASK ─────────────────────────────────────────────
            slug = request.slug or Stack__Name__Generator().generate()
            task = None
            with timer.phase(Enum__VAF__Start__Phase.RUN_TASK.value) as result:
                self.slug_resolver.check_unique(cluster_cfg.cluster_name, slug)
                task_tags = dict(request.tags or {})
                task_tags['VaultApp__Slug'] = slug
                subnets = [s.strip() for s in cluster_cfg.subnets.split(',') if s.strip()]
                task = self.fargate_client.run_task(
                    cluster          = cluster_cfg.cluster_name,
                    task_def         = self.spec.default_task_def_family,
                    subnets          = subnets,
                    security_groups  = [cluster_cfg.security_group] if cluster_cfg.security_group else [],
                    assign_public_ip = request.public_ip,
                    launch_type      = request.launch_type,
                    tags             = task_tags,
                    env              = self.spec.env_for_run(
                        access_token    = request.access_token,
                        seed_vault_keys = request.seed_vault_keys,
                        with_tls        = request.with_tls,
                    ),
                )
                report.task_arn     = str(task.task_arn) if task else ''
                report.cluster_name = cluster_cfg.cluster_name
                report.slug         = slug
                result.detail       = f'task={report.task_arn[-12:] if report.task_arn else "?"}'

            # ── Phase 3: WAIT_RUNNING ─────────────────────────────────────────
            with timer.phase(Enum__VAF__Start__Phase.WAIT_RUNNING.value) as result:
                for attempt in range(30):
                    task        = self.fargate_client.describe_task(report.task_arn, cluster_cfg.cluster_name)
                    status      = str(task.status) if task else 'MISSING'
                    stop_reason = str(task.stopped_reason) if task and task.stopped_reason else ''
                    result.detail = f'state: {status} (attempt {attempt + 1})'
                    if status == 'RUNNING':
                        break
                    if status in ('STOPPED', 'DEPROVISIONING'):
                        msg = f'Task stopped unexpectedly: {status}'
                        if stop_reason:
                            msg = f'{msg} — {stop_reason}'
                        raise RuntimeError(msg)
                    _time.sleep(1)
                else:
                    raise RuntimeError('Task did not reach RUNNING within 30s')
                report.task_definition = str(task.task_definition) if task else ''

            report.task_ready_ms = timer.cumulative_through(Enum__VAF__Start__Phase.WAIT_RUNNING.value)

            # ── Phase 4: RESOLVE_ENI ──────────────────────────────────────────
            with timer.phase(Enum__VAF__Start__Phase.RESOLVE_ENI.value) as result:
                eni_id = self._extract_eni_id(task)
                if eni_id and self.ec2_client:
                    eni = self.ec2_client.describe_network_interface(eni_id)
                    report.public_ip  = str(eni.public_ip)  if eni else ''
                    report.private_ip = str(eni.private_ip) if eni else ''
                result.detail = f'ip={report.public_ip or "none"}'

            # ── Phase 5: DNS_UPSERT — v1 stub ─────────────────────────────────
            # with_aws_dns is not implemented in v1; skip the phase entirely

            # ── Phase 6: WAIT_HEALTH ──────────────────────────────────────────
            port      = self.spec.https_port if request.with_tls else self.spec.http_port
            scheme    = 'https' if request.with_tls else 'http'
            host      = report.public_ip or report.private_ip
            vault_url = f'{scheme}://{host}:{port}'
            report.vault_url    = vault_url
            report.access_token = request.access_token
            with timer.phase(Enum__VAF__Start__Phase.WAIT_HEALTH.value) as result:
                health_result = self.health.wait_for(
                    url          = vault_url + self.spec.health_path,
                    access_token = request.access_token,
                )
                result.detail = f'attempts={health_result.attempts} ok={health_result.ok}'
                if not health_result.ok:
                    raise RuntimeError(
                        f'Health check failed after {health_result.attempts} attempts: '
                        f'{health_result.last_error}'
                    )

            report.phases         = timer.results
            report.vault_ready_ms = timer.cumulative_through(Enum__VAF__Start__Phase.WAIT_HEALTH.value)
            report.total_ms       = timer.total_ms()
            report.ok             = True

            self.timings_store.append(Schema__VAF__Timings__Record(
                slug           = slug,
                cluster_name   = cluster_cfg.cluster_name,
                task_ready_ms  = report.task_ready_ms,
                vault_ready_ms = report.vault_ready_ms,
                total_ms       = report.total_ms,
                launch_type    = request.launch_type,
                executed_at    = report.executed_at,
            ))

        except Exception as exc:
            report.phases  = timer.results
            report.total_ms = timer.total_ms()
            report.ok      = False
            report.error   = str(exc)
            raise

        return report

    # ── internal ──────────────────────────────────────────────────────────────

    def _extract_eni_id(self, task) -> str:                                       # read eni_id field populated by _parse_task
        if task is None:
            return ''
        return str(task.eni_id) if task.eni_id else ''
