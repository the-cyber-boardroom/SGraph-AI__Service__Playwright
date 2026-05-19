# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute_specs vault_app/fargate — Vault_App__Fargate__Setup
# One-time provisioning orchestrator for all cluster-level AWS resources.
# Drives six phases (ECR → IAM → LOGS → CLUSTER → IMAGE_MIRROR → TASK_DEF)
# in dependency order for create/update; reversed for delete; parallel for check.
#
# Injects in-memory clients for unit tests (no mocks, no patches).
# progress_cb: callable(phase_name, status, detail='') or None.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute_specs.vault_app.fargate.enums.Enum__VAF__Phase__Status         import Enum__VAF__Phase__Status
from sg_compute_specs.vault_app.fargate.enums.Enum__VAF__Setup__Phase          import Enum__VAF__Setup__Phase
from sg_compute_specs.vault_app.fargate.schemas.Schema__VAF__Setup__Report     import Schema__VAF__Setup__Report
from sg_compute_specs.vault_app.fargate.schemas.Schema__VAF__Setup__Request    import Schema__VAF__Setup__Request
from sg_compute_specs.vault_app.fargate.service.Phase__Timer                   import Phase__Timer
from sg_compute_specs.vault_app.fargate.service.Vault_App__Fargate__Image__Mirror import Vault_App__Fargate__Image__Mirror
from sg_compute_specs.vault_app.fargate.service.Vault_App__Fargate__Spec        import Vault_App__Fargate__Spec
from sg_compute_specs.vault_app.fargate.service.Vault_App__Fargate__Tags__Reader import Vault_App__Fargate__Tags__Reader
from sg_compute_specs.vault_app.fargate.service.Vault_App__Fargate__Tags__Writer import Vault_App__Fargate__Tags__Writer


_ECS_TASK_EXECUTION_POLICY = 'arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy'


class Vault_App__Fargate__Setup(Type_Safe):
    spec           : Vault_App__Fargate__Spec          = None
    tags_writer    : Vault_App__Fargate__Tags__Writer  = None
    tags_reader    : Vault_App__Fargate__Tags__Reader  = None
    image_mirror   : Vault_App__Fargate__Image__Mirror = None

    ecr_client     : object = None                                                # ECR__AWS__Client   — injected
    fargate_client : object = None                                                # Fargate__AWS__Client — injected
    logs_client    : object = None                                                # Logs__AWS__Client  — injected
    iam_client     : object = None                                                # IAM__AWS__Client   — injected

    progress_cb    : object = None                                                # callable(phase_name, status, detail='') or None

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def setup(self):                                                              # initialise defaults if None
        if not self.spec:
            self.spec         = Vault_App__Fargate__Spec()
        if not self.tags_writer:
            self.tags_writer  = Vault_App__Fargate__Tags__Writer()
        if not self.tags_reader:
            self.tags_reader  = Vault_App__Fargate__Tags__Reader(fargate_client=self.fargate_client)
        if not self.image_mirror:
            self.image_mirror = Vault_App__Fargate__Image__Mirror()

    # ── public operations ─────────────────────────────────────────────────────

    def check(self, request: Schema__VAF__Setup__Request) -> Schema__VAF__Setup__Report:
        return self._run('check', request)                                        # runs all phases; never stops on error

    def create(self, request: Schema__VAF__Setup__Request) -> Schema__VAF__Setup__Report:
        return self._run('create', request)

    def update(self, request: Schema__VAF__Setup__Request) -> Schema__VAF__Setup__Report:
        return self._run('update', request)

    def delete(self, request: Schema__VAF__Setup__Request) -> Schema__VAF__Setup__Report:
        return self._run('delete', request)                                       # phases run in reverse order

    # ── orchestration loop ────────────────────────────────────────────────────

    def _run(self, op: str, request: Schema__VAF__Setup__Request) -> Schema__VAF__Setup__Report:
        self.setup()
        timer  = Phase__Timer(progress_cb=self.progress_cb)
        phases = list(request.phases or list(Enum__VAF__Setup__Phase))
        if op == 'delete':
            phases = list(reversed(phases))

        cluster_name = request.cluster_name or self.spec.default_cluster
        ctx = {                                                                    # threaded across phases so IAM ARN reaches CLUSTER/TASK_DEF
            'cluster_name'       : cluster_name,
            'region'             : self._resolve_region(request),
            'execution_role_arn' : '',                                             # populated by _phase_iam create/check
        }

        for phase_enum in phases:
            with timer.phase(phase_enum.value) as result:
                self._dispatch_phase(op, phase_enum, request, result, ctx)
            last = timer.results[-1]
            is_error = last.status == Enum__VAF__Phase__Status.ERROR
            if is_error and op != 'check' and not request.continue_on_error:
                break

        all_ok = all(
            r.status in (Enum__VAF__Phase__Status.OK, Enum__VAF__Phase__Status.SKIPPED)
            for r in (timer.results or [])
        )
        return Schema__VAF__Setup__Report(
            cluster_name = cluster_name,
            operation    = op,
            phases       = timer.results,
            total_ms     = timer.total_ms(),
            ok           = all_ok,
        )

    def _resolve_region(self, request: Schema__VAF__Setup__Request) -> str:        # explicit → client → empty (caller error)
        if request.region:
            return request.region
        if self.fargate_client and hasattr(self.fargate_client, 'current_region'):
            return self.fargate_client.current_region() or ''
        return ''

    def _dispatch_phase(self, op: str, phase: Enum__VAF__Setup__Phase,
                        request: Schema__VAF__Setup__Request, result, ctx: dict) -> None:
        if phase == Enum__VAF__Setup__Phase.ECR:
            self._phase_ecr(op, request, result, ctx)
        elif phase == Enum__VAF__Setup__Phase.IAM:
            self._phase_iam(op, request, result, ctx)
        elif phase == Enum__VAF__Setup__Phase.LOGS:
            self._phase_logs(op, request, result, ctx)
        elif phase == Enum__VAF__Setup__Phase.CLUSTER:
            self._phase_cluster(op, request, result, ctx)
        elif phase == Enum__VAF__Setup__Phase.IMAGE_MIRROR:
            self._phase_image_mirror(op, request, result, ctx)
        elif phase == Enum__VAF__Setup__Phase.TASK_DEF:
            self._phase_task_def(op, request, result, ctx)

    # ── phase: ECR ────────────────────────────────────────────────────────────

    def _phase_ecr(self, op: str, request: Schema__VAF__Setup__Request, result, ctx: dict) -> None:
        repo_name = request.ecr_repo_name or self.spec.image_repo_name
        if not self.ecr_client:
            result.status = Enum__VAF__Phase__Status.SKIPPED
            result.detail = 'ecr_client not provided'
            return

        if op == 'check':
            repo = self.ecr_client.describe_repository(repo_name)
            result.detail = 'exists' if repo else 'missing'
            result.status = Enum__VAF__Phase__Status.OK

        elif op == 'create':
            created = self.ecr_client.create_repository(repo_name)
            if created:                                                           # True = newly created
                result.detail = f'created {repo_name}'
                result.status = Enum__VAF__Phase__Status.OK
            else:                                                                 # False = already existed
                result.detail = 'already exists'
                result.status = Enum__VAF__Phase__Status.SKIPPED

        elif op == 'update':
            repo = self.ecr_client.describe_repository(repo_name)                # no update needed in v1
            result.detail = 'exists' if repo else 'missing'
            result.status = Enum__VAF__Phase__Status.OK

        elif op == 'delete':
            deleted = self.ecr_client.delete_repository(repo_name, force=True)
            if deleted:
                result.detail = f'deleted {repo_name}'
                result.status = Enum__VAF__Phase__Status.OK
            else:
                result.detail = 'not found'
                result.status = Enum__VAF__Phase__Status.SKIPPED

    # ── phase: IAM ────────────────────────────────────────────────────────────

    def _phase_iam(self, op: str, request: Schema__VAF__Setup__Request, result, ctx: dict) -> None:
        if not self.iam_client:
            result.status = Enum__VAF__Phase__Status.SKIPPED
            result.detail = 'iam_client not provided'
            return

        role_name = request.execution_role_name

        if op == 'check':
            role = self._read_iam_role(role_name)
            if role:
                ctx['execution_role_arn'] = role
                result.detail = f'exists ({role})'
            else:
                result.detail = 'missing'
            result.status = Enum__VAF__Phase__Status.OK

        elif op == 'create':
            from sgraph_ai_service_playwright__cli.aws.iam.enums.Enum__IAM__Trust__Service      import Enum__IAM__Trust__Service
            from sgraph_ai_service_playwright__cli.aws.iam.schemas.Schema__IAM__Role__Create__Request import Schema__IAM__Role__Create__Request
            req = Schema__IAM__Role__Create__Request(
                role_name     = role_name,
                trust_service = Enum__IAM__Trust__Service.ECS_TASKS,
                description   = 'Vault App Fargate execution role',
            )
            resp = self.iam_client.create_role(req)
            self.iam_client.attach_managed_policy(role_name, _ECS_TASK_EXECUTION_POLICY)
            ctx['execution_role_arn'] = str(resp.role_arn or '')                  # thread ARN to later phases
            if resp.created:
                result.detail = f'created role {role_name}'
                result.status = Enum__VAF__Phase__Status.OK
            else:
                result.detail = 'already exists'
                result.status = Enum__VAF__Phase__Status.SKIPPED

        elif op == 'update':                                                      # re-attach policy if missing
            exists = self.iam_client.role_exists(role_name)
            if exists:
                self.iam_client.attach_managed_policy(role_name, _ECS_TASK_EXECUTION_POLICY)
                ctx['execution_role_arn'] = self._read_iam_role(role_name)
                result.detail = 'policy ensured'
                result.status = Enum__VAF__Phase__Status.OK
            else:
                result.detail = 'missing'
                result.status = Enum__VAF__Phase__Status.OK

        elif op == 'delete':
            deleted = self.iam_client.delete_role(role_name)
            if deleted:
                result.detail = f'deleted role {role_name}'
                result.status = Enum__VAF__Phase__Status.OK
            else:
                result.detail = 'not found'
                result.status = Enum__VAF__Phase__Status.SKIPPED

    def _read_iam_role(self, role_name: str) -> str:                              # tolerate clients that don't expose describe
        for method in ('describe_role', 'get_role'):
            fn = getattr(self.iam_client, method, None)
            if fn is None:
                continue
            try:
                role = fn(role_name)
                if role is None:
                    return ''
                arn = getattr(role, 'role_arn', '') or getattr(role, 'arn', '')
                return str(arn or '')
            except Exception:
                return ''
        return ''

    # ── phase: LOGS ───────────────────────────────────────────────────────────

    def _phase_logs(self, op: str, request: Schema__VAF__Setup__Request, result, ctx: dict) -> None:
        log_group = request.log_group or self.spec.default_log_group
        if not self.logs_client:
            result.status = Enum__VAF__Phase__Status.SKIPPED
            result.detail = 'logs_client not provided'
            return

        if op == 'check':
            group = self.logs_client.describe_log_group(log_group)
            result.detail = 'exists' if group else 'missing'
            result.status = Enum__VAF__Phase__Status.OK

        elif op == 'create':
            group = self.logs_client.describe_log_group(log_group)
            if group:
                result.detail = 'already exists'
                result.status = Enum__VAF__Phase__Status.SKIPPED
            else:
                self.logs_client.create_log_group(log_group, retention_days=7)
                result.detail = f'created {log_group}'
                result.status = Enum__VAF__Phase__Status.OK

        elif op == 'update':
            updated = self.logs_client.update_retention(log_group, days=7)        # via service-layer method, not raw boto3
            if updated:
                result.detail = 'retention updated'
            else:
                result.detail = 'missing'
            result.status = Enum__VAF__Phase__Status.OK

        elif op == 'delete':
            deleted = self.logs_client.delete_log_group(log_group)
            if deleted:
                result.detail = f'deleted {log_group}'
                result.status = Enum__VAF__Phase__Status.OK
            else:
                result.detail = 'not found'
                result.status = Enum__VAF__Phase__Status.SKIPPED

    # ── phase: CLUSTER ────────────────────────────────────────────────────────

    def _phase_cluster(self, op: str, request: Schema__VAF__Setup__Request, result, ctx: dict) -> None:
        cluster_name = ctx['cluster_name']
        if not self.fargate_client:
            result.status = Enum__VAF__Phase__Status.SKIPPED
            result.detail = 'fargate_client not provided'
            return

        if op == 'check':
            cluster = self.fargate_client.describe_cluster(cluster_name)
            result.detail = 'active' if cluster else 'missing'
            result.status = Enum__VAF__Phase__Status.OK

        elif op == 'create':
            existing = self.fargate_client.describe_cluster(cluster_name)
            if existing:
                network_tags = {}
                if request.subnets:
                    network_tags['VaultApp__Subnets'] = request.subnets.replace(',', ' ')   # AWS tag values disallow commas
                if request.security_group:
                    network_tags['VaultApp__SecurityGroup'] = request.security_group
                if network_tags:
                    self.fargate_client.tag_cluster(cluster_name, network_tags)
                    result.detail = 'retagged network config'
                    result.status = Enum__VAF__Phase__Status.OK
                else:
                    result.detail = 'already exists'
                    result.status = Enum__VAF__Phase__Status.SKIPPED
            else:
                log_group      = request.log_group       or self.spec.default_log_group
                ecr_repo_name  = request.ecr_repo_name   or self.spec.image_repo_name
                tags = self.tags_writer.tags_for_cluster(
                    cluster_name       = cluster_name,
                    subnets            = request.subnets,
                    security_group     = request.security_group,
                    execution_role_arn = ctx['execution_role_arn'],                # populated by _phase_iam (runs first)
                    log_group          = log_group,
                    ecr_repo_name      = ecr_repo_name,
                    region             = ctx['region'],
                    task_role_arn      = request.task_role_name,
                    dns_zone           = request.dns_zone,
                )
                self.fargate_client.create_cluster(cluster_name, tags=tags)
                result.detail = f'created {cluster_name}'
                result.status = Enum__VAF__Phase__Status.OK

        elif op == 'update':                                                      # retag cluster with whatever the request carries
            existing = self.fargate_client.describe_cluster(cluster_name)
            if existing:
                network_tags = {}
                if request.subnets:
                    network_tags['VaultApp__Subnets'] = request.subnets.replace(',', ' ')   # AWS tag values disallow commas
                if request.security_group:
                    network_tags['VaultApp__SecurityGroup'] = request.security_group
                if network_tags:
                    self.fargate_client.tag_cluster(cluster_name, network_tags)
                    result.detail = 'retagged network config'
                else:
                    result.detail = 'exists'
                result.status = Enum__VAF__Phase__Status.OK
            else:
                result.detail = 'missing'
                result.status = Enum__VAF__Phase__Status.OK

        elif op == 'delete':
            existing = self.fargate_client.describe_cluster(cluster_name)
            if existing:
                self.fargate_client.delete_cluster(cluster_name)
                result.detail = f'deleted {cluster_name}'
                result.status = Enum__VAF__Phase__Status.OK
            else:
                result.detail = 'not found'
                result.status = Enum__VAF__Phase__Status.SKIPPED

    # ── phase: IMAGE_MIRROR ───────────────────────────────────────────────────

    def _phase_image_mirror(self, op: str, request: Schema__VAF__Setup__Request, result, ctx: dict) -> None:
        repo_name = request.ecr_repo_name or self.spec.image_repo_name
        region    = ctx['region']
        ecr_uri   = ''
        registry  = ''

        if op == 'delete':                                                        # images deleted with the ECR repo
            result.detail = 'skipped (ECR repo deletion handles images)'
            result.status = Enum__VAF__Phase__Status.SKIPPED
            return

        if self.ecr_client and region:
            repo = self.ecr_client.describe_repository(repo_name)
            if repo:
                registry = f'{repo.registry_id}.dkr.ecr.{region}.amazonaws.com'
                ecr_uri  = f'{registry}/{repo_name}'

        if op == 'check':
            if not self.ecr_client:
                result.detail = 'ecr_client not provided'
                result.status = Enum__VAF__Phase__Status.SKIPPED
                return
            images = self.ecr_client.list_images(repo_name)
            has_images = images is not None and len(list(images)) > 0
            result.detail = 'images present' if has_images else 'no images'
            result.status = Enum__VAF__Phase__Status.OK
            return

        if not ecr_uri:
            if not region:
                result.detail = 'region could not be resolved — pass --region or configure session'
            else:
                result.detail = 'ecr_uri could not be resolved — run ECR phase first'
            result.status = Enum__VAF__Phase__Status.ERROR
            return

        # wire live progress: stream docker output into the phase Detail column
        phase_name = Enum__VAF__Setup__Phase.IMAGE_MIRROR.value
        progress_cb = self.progress_cb

        def step_cb(step_name: str, line: str) -> None:
            if not progress_cb:
                return
            short = line if len(line) <= 70 else line[:67] + '...'
            progress_cb(phase_name, Enum__VAF__Phase__Status.RUNNING,
                        f'{step_name}: {short}')

        self.image_mirror.step_cb  = step_cb
        self.image_mirror.region   = region
        self.image_mirror.registry = registry
        self.image_mirror.ecr_client = self.ecr_client

        mirror_result = self.image_mirror.mirror(request.source_image, ecr_uri)
        if mirror_result.get('ok'):
            sha     = mirror_result.get('sha', '')
            skipped = mirror_result.get('skipped', False)
            if skipped:
                result.detail = f'already in ECR ({sha[:23]}...)' if sha else 'already in ECR'
                result.status = Enum__VAF__Phase__Status.SKIPPED
            else:
                result.detail = f'sha={sha}'
                result.status = Enum__VAF__Phase__Status.OK
        else:
            steps  = mirror_result.get('steps', [])
            last   = steps[-1] if steps else {}
            stderr = (last.get('stderr') or last.get('stdout') or 'unknown error')
            # Trim multi-line errors to first non-empty line for the Detail column
            first_line = next((l for l in stderr.splitlines() if l.strip()), stderr)
            result.detail = f'mirror failed: {first_line[:120]}'
            result.status = Enum__VAF__Phase__Status.ERROR

    # ── phase: TASK_DEF ───────────────────────────────────────────────────────

    def _phase_task_def(self, op: str, request: Schema__VAF__Setup__Request, result, ctx: dict) -> None:
        family = self.spec.default_task_def_family                                # always the spec family, NOT cluster name
        if not self.fargate_client:
            result.status = Enum__VAF__Phase__Status.SKIPPED
            result.detail = 'fargate_client not provided'
            return

        if op == 'check':
            td = self.fargate_client.describe_task_definition(family)
            if td:
                result.detail = f'revision :{td.revision}'
                result.status = Enum__VAF__Phase__Status.OK
            else:
                result.detail = 'missing'
                result.status = Enum__VAF__Phase__Status.OK

        elif op in ('create', 'update'):                                          # registers a new revision
            repo_name = request.ecr_repo_name or self.spec.image_repo_name
            region    = ctx['region']
            image_uri = ''
            if self.ecr_client:
                repo = self.ecr_client.describe_repository(repo_name)
                if repo and region:
                    image_uri = f'{repo.registry_id}.dkr.ecr.{region}.amazonaws.com/{repo_name}:latest'

            if not image_uri:
                result.detail = ('image uri could not be resolved — '
                                 'ensure ECR repo exists and region is set')
                result.status = Enum__VAF__Phase__Status.ERROR
                return

            log_group = request.log_group or self.spec.default_log_group
            td = self.fargate_client.register_task_definition(
                name               = family,
                image              = image_uri,
                cpu                = request.cpu   or self.spec.default_cpu,
                memory             = request.memory or self.spec.default_memory,
                port_mappings      = self.spec.port_mappings(),
                execution_role_arn = ctx['execution_role_arn'],                   # populated by _phase_iam (runs first)
                log_group          = log_group,
            )
            result.detail = f'revision :{td.revision}'
            result.status = Enum__VAF__Phase__Status.OK

        elif op == 'delete':
            td = self.fargate_client.describe_task_definition(family)
            if td:
                result.detail = f'deregister not implemented in fargate_client v1'
                result.status = Enum__VAF__Phase__Status.SKIPPED
            else:
                result.detail = 'not found'
                result.status = Enum__VAF__Phase__Status.SKIPPED
