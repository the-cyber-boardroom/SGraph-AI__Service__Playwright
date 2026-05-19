# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Fargate__AWS__Client
# Sole boto3 boundary for ECS Fargate operations.  Covers clusters, task
# definitions, tasks, and log-group discovery.
#
# Credentials are resolved via Sg__Aws__Session.from_context() so that
# `sg credentials switch dev` is honoured by all ECS calls.
# Subclasses override client() to inject fakes for unit tests.
# ═══════════════════════════════════════════════════════════════════════════════

from typing import Optional

from botocore.exceptions import ClientError
from osbot_utils.type_safe.Type_Safe                                              import Type_Safe

from sgraph_ai_service_playwright__cli.aws.fargate.collections.List__Schema__ECS__Cluster        import List__Schema__ECS__Cluster
from sgraph_ai_service_playwright__cli.aws.fargate.collections.List__Schema__ECS__Task           import List__Schema__ECS__Task
from sgraph_ai_service_playwright__cli.aws.fargate.collections.List__Schema__ECS__Task__Definition import List__Schema__ECS__Task__Definition
from sgraph_ai_service_playwright__cli.aws.fargate.enums.Enum__ECS__Launch__Type                  import Enum__ECS__Launch__Type
from sgraph_ai_service_playwright__cli.aws.fargate.enums.Enum__ECS__Task__Status                  import Enum__ECS__Task__Status
from sgraph_ai_service_playwright__cli.aws.fargate.primitives.Safe_Str__ECS__Cluster__Name        import Safe_Str__ECS__Cluster__Name
from sgraph_ai_service_playwright__cli.aws.fargate.primitives.Safe_Str__ECS__Task__ARN            import Safe_Str__ECS__Task__ARN
from sgraph_ai_service_playwright__cli.aws.fargate.primitives.Safe_Str__ECS__Task__Definition     import Safe_Str__ECS__Task__Definition
from sgraph_ai_service_playwright__cli.aws.fargate.schemas.Schema__ECS__Cluster                   import Schema__ECS__Cluster
from sgraph_ai_service_playwright__cli.aws.fargate.schemas.Schema__ECS__Task                      import Schema__ECS__Task
from sgraph_ai_service_playwright__cli.aws.fargate.schemas.Schema__ECS__Task__Definition          import Schema__ECS__Task__Definition
from sgraph_ai_service_playwright__cli.credentials.service.Sg__Aws__Session                       import Sg__Aws__Session


class Fargate__AWS__Client(Type_Safe):
    session : Sg__Aws__Session = None                                             # cached session — injected or lazy-init via setup()
    region  : str              = ''                                               # override to target a specific region

    def setup(self):                                                              # idempotent — noop if session already set
        if self.session is None:
            self.session = Sg__Aws__Session.from_context()
        return self

    def client(self):                                                             # single boto3 seam — subclass overrides for tests
        self.setup()
        return self.session.boto3_client_from_context('ecs', region=self.region)

    def current_region(self) -> str:                                              # resolved region (explicit override → boto3 client meta)
        if self.region:
            return self.region
        try:
            meta = getattr(self.client(), 'meta', None)
            return getattr(meta, 'region_name', '') or ''
        except Exception:
            return ''

    # ── cluster read ──────────────────────────────────────────────────────────

    def list_clusters(self) -> List__Schema__ECS__Cluster:
        ecs    = self.client()
        arns   = []
        kwargs = {}
        while True:
            resp = ecs.list_clusters(**kwargs)
            arns.extend(resp.get('clusterArns', []))
            next_token = resp.get('nextToken')
            if not next_token:
                break
            kwargs['nextToken'] = next_token
        if not arns:
            return List__Schema__ECS__Cluster()
        desc = ecs.describe_clusters(clusters=arns, include=['SETTINGS', 'STATISTICS', 'TAGS'])
        result = List__Schema__ECS__Cluster()
        for raw in desc.get('clusters', []):
            result.append(self._parse_cluster(raw))
        return result

    def describe_cluster(self, name: str) -> Optional[Schema__ECS__Cluster]:
        try:
            resp     = self.client().describe_clusters(clusters=[name], include=['SETTINGS', 'STATISTICS', 'TAGS'])
            clusters = resp.get('clusters', [])
            if not clusters:
                return None
            return self._parse_cluster(clusters[0])
        except ClientError as exc:
            code = exc.response.get('Error', {}).get('Code', '')
            if code == 'ClusterNotFoundException':
                return None
            raise

    # ── cluster mutations ─────────────────────────────────────────────────────

    def create_cluster(self, name: str, tags: dict = None) -> Schema__ECS__Cluster:
        tag_list = [{'key': k, 'value': v} for k, v in (tags or {}).items()]
        tag_list.append({'key': 'sg:managed', 'value': 'true'})
        resp = self.client().create_cluster(
            clusterName         = name,
            capacityProviders   = ['FARGATE', 'FARGATE_SPOT'],
            defaultCapacityProviderStrategy = [
                {'capacityProvider': 'FARGATE', 'weight': 1, 'base': 1},
            ],
            settings            = [{'name': 'containerInsights', 'value': 'enabled'}],
            tags                = tag_list,
        )
        return self._parse_cluster(resp['cluster'])

    def delete_cluster(self, name: str) -> None:
        cluster = self.describe_cluster(name)
        if cluster and cluster.running_tasks > 0:
            raise ValueError(f'Cluster "{name}" has {cluster.running_tasks} running tasks — stop them first.')
        self.client().delete_cluster(cluster=name)

    # ── task-def read ─────────────────────────────────────────────────────────

    def list_task_definitions(self, family: str = '') -> List__Schema__ECS__Task__Definition:
        ecs    = self.client()
        arns   = []
        kwargs = {'status': 'ACTIVE'}
        if family:
            kwargs['familyPrefix'] = family
        while True:
            resp = ecs.list_task_definitions(**kwargs)
            arns.extend(resp.get('taskDefinitionArns', []))
            next_token = resp.get('nextToken')
            if not next_token:
                break
            kwargs['nextToken'] = next_token
        result = List__Schema__ECS__Task__Definition()
        for arn in arns:
            td = self._parse_task_def_from_arn(arn)
            if td:
                result.append(td)
        return result

    def describe_task_definition(self, family_rev: str) -> Optional[Schema__ECS__Task__Definition]:
        try:
            resp = self.client().describe_task_definition(taskDefinition=family_rev, include=['TAGS'])
            raw  = resp.get('taskDefinition', {})
            return self._parse_task_def_full(raw)
        except ClientError as exc:
            code = exc.response.get('Error', {}).get('Code', '')
            if code in ('ClientException', 'InvalidParameterException'):
                return None
            raise

    # ── task-def mutation ─────────────────────────────────────────────────────

    def register_task_definition(self, name: str, image: str,
                                  cpu: str = '256', memory: str = '512',
                                  env: dict = None,
                                  port_mappings: list = None,
                                  execution_role_arn: str = '',
                                  task_role_arn: str = '',
                                  log_group: str = '') -> Schema__ECS__Task__Definition:
        env_list    = [{'name': k, 'value': v} for k, v in (env or {}).items()]
        mapped_ports = port_mappings or []
        active_log_group = log_group or f'/ecs/{name}'
        container_def = {
            'name'       : name,
            'image'      : image,
            'essential'  : True,
            'environment': env_list,
            'logConfiguration': {
                'logDriver': 'awslogs',
                'options'  : {
                    'awslogs-group'        : active_log_group,
                    'awslogs-region'       : self.region or 'us-east-1',
                    'awslogs-stream-prefix': 'ecs',
                },
            },
        }
        if mapped_ports:
            container_def['portMappings'] = [
                {'containerPort': int(p.get('containerPort', 0)),
                 'protocol'     : p.get('protocol', 'tcp')}
                for p in mapped_ports
            ]
        kwargs = dict(
            family                  = name,
            networkMode             = 'awsvpc',
            requiresCompatibilities = ['FARGATE'],
            cpu                     = cpu,
            memory                  = memory,
            containerDefinitions    = [container_def],
        )
        if execution_role_arn:
            kwargs['executionRoleArn'] = execution_role_arn
        if task_role_arn:
            kwargs['taskRoleArn'] = task_role_arn
        resp = self.client().register_task_definition(**kwargs)
        return self._parse_task_def_full(resp.get('taskDefinition', {}),
                                         port_mappings=mapped_ports,
                                         execution_role_arn=execution_role_arn,
                                         task_role_arn=task_role_arn,
                                         log_group=active_log_group)

    # ── task read ─────────────────────────────────────────────────────────────

    def list_tasks(self, cluster: str = '', family: str = '') -> List__Schema__ECS__Task:
        ecs    = self.client()
        arns   = []
        kwargs = {'desiredStatus': 'RUNNING'}
        if cluster:
            kwargs['cluster'] = cluster
        if family:
            kwargs['family'] = family
        while True:
            resp = ecs.list_tasks(**kwargs)
            arns.extend(resp.get('taskArns', []))
            next_token = resp.get('nextToken')
            if not next_token:
                break
            kwargs['nextToken'] = next_token
        if not arns:
            return List__Schema__ECS__Task()
        desc_kwargs = {'tasks': arns}
        if cluster:
            desc_kwargs['cluster'] = cluster
        desc   = ecs.describe_tasks(**desc_kwargs)
        result = List__Schema__ECS__Task()
        for raw in desc.get('tasks', []):
            result.append(self._parse_task(raw))
        return result

    def describe_task(self, task_arn: str, cluster: str = '') -> Optional[Schema__ECS__Task]:
        kwargs = {'tasks': [task_arn]}
        if cluster:
            kwargs['cluster'] = cluster
        resp  = self.client().describe_tasks(**kwargs)
        tasks = resp.get('tasks', [])
        if not tasks:
            return None
        return self._parse_task(tasks[0])

    # ── task mutations ────────────────────────────────────────────────────────

    def run_task(self, cluster: str, task_def: str,
                 count: int = 1, subnets: list = None,
                 security_groups: list = None,
                 assign_public_ip: bool = False,
                 launch_type: str = 'FARGATE',
                 tags: dict = None,
                 env: dict = None) -> Optional[Schema__ECS__Task]:
        vpc_config = {
            'awsvpcConfiguration': {
                'subnets'        : subnets or [],
                'securityGroups' : security_groups or [],
                'assignPublicIp' : 'ENABLED' if assign_public_ip else 'DISABLED',
            }
        }
        tag_list = [{'key': 'sg:managed', 'value': 'true'}]
        if tags:
            tag_list.extend([{'key': k, 'value': v} for k, v in tags.items()])
        run_kwargs = dict(
            cluster              = cluster,
            taskDefinition       = task_def,
            count                = count,
            launchType           = launch_type,
            networkConfiguration = vpc_config,
            tags                 = tag_list,
        )
        if env:                                                                    # override env via containerOverrides
            run_kwargs['overrides'] = {
                'containerOverrides': [{
                    'name'       : task_def.split(':')[0],                         # use family name as container name
                    'environment': [{'name': k, 'value': v} for k, v in env.items()],
                }]
            }
        resp  = self.client().run_task(**run_kwargs)
        tasks = resp.get('tasks', [])
        if not tasks:
            return None
        return self._parse_task(tasks[0], launch_type=launch_type, tags=tags)

    def stop_task(self, task_arn: str, cluster: str = '', reason: str = '') -> None:
        kwargs = {'task': task_arn}
        if cluster:
            kwargs['cluster'] = cluster
        if reason:
            kwargs['reason'] = reason
        self.client().stop_task(**kwargs)

    # ── log group discovery ───────────────────────────────────────────────────

    def log_group_for_task_def(self, family: str) -> str:
        return f'/ecs/{family}'                                                   # convention used by register_task_definition

    # ── internal ──────────────────────────────────────────────────────────────

    def _parse_cluster(self, raw: dict) -> Schema__ECS__Cluster:
        name     = raw.get('clusterName', '')
        raw_tags = raw.get('tags', [])                                             # AWS returns [{key, value}, ...]
        tags     = {t['key']: t['value'] for t in raw_tags if 'key' in t}         # normalise to plain dict
        return Schema__ECS__Cluster(
            cluster_name    = Safe_Str__ECS__Cluster__Name(name) if name else Safe_Str__ECS__Cluster__Name(''),
            cluster_arn     = raw.get('clusterArn', ''),
            status          = raw.get('status', ''),
            running_tasks   = raw.get('runningTasksCount', 0),
            pending_tasks   = raw.get('pendingTasksCount', 0),
            active_services = raw.get('activeServicesCount', 0),
            tags            = tags,
        )

    def _parse_task_def_from_arn(self, arn: str) -> Optional[Schema__ECS__Task__Definition]:
        # arn:aws:ecs:<region>:<account>:task-definition/<family>:<rev>
        try:
            tail   = arn.split('task-definition/')[-1]          # e.g. "my-task:3"
            parts  = tail.split(':')
            family = parts[0]
            rev    = int(parts[1]) if len(parts) > 1 else 0
            return Schema__ECS__Task__Definition(
                family          = family,
                revision        = rev,
                task_def_arn    = arn,
                status          = 'ACTIVE',
                family_revision = Safe_Str__ECS__Task__Definition(tail),
            )
        except (ValueError, IndexError):
            return None

    def _parse_task_def_full(self, raw: dict,
                              port_mappings: list = None,
                              execution_role_arn: str = '',
                              task_role_arn: str = '',
                              log_group: str = '') -> Schema__ECS__Task__Definition:
        from sgraph_ai_service_playwright__cli.aws.fargate.collections.List__Schema__ECS__Port_Mapping import List__Schema__ECS__Port_Mapping
        from sgraph_ai_service_playwright__cli.aws.fargate.schemas.Schema__ECS__Port_Mapping           import Schema__ECS__Port_Mapping
        family  = raw.get('family', '')
        rev     = raw.get('revision', 0)
        pm_list = List__Schema__ECS__Port_Mapping()
        for pm in (port_mappings or []):
            pm_list.append(Schema__ECS__Port_Mapping(
                container_port = int(pm.get('containerPort', 0)),
                protocol       = pm.get('protocol', 'tcp'),
            ))
        return Schema__ECS__Task__Definition(
            family             = family,
            revision           = rev,
            task_def_arn       = raw.get('taskDefinitionArn', ''),
            status             = raw.get('status', ''),
            cpu                = str(raw.get('cpu', '')),
            memory             = str(raw.get('memory', '')),
            launch_type        = Enum__ECS__Launch__Type.FARGATE,
            family_revision    = Safe_Str__ECS__Task__Definition(f'{family}:{rev}' if family else ''),
            port_mappings      = pm_list,
            execution_role_arn = execution_role_arn or raw.get('executionRoleArn', ''),
            task_role_arn      = task_role_arn      or raw.get('taskRoleArn', ''),
            log_group          = log_group,
        )

    def _parse_task(self, raw: dict,
                    launch_type: str = '',
                    tags: dict = None) -> Schema__ECS__Task:
        task_arn   = raw.get('taskArn', '')
        cluster_arn= raw.get('clusterArn', '')
        cluster_name = cluster_arn.split('/')[-1] if '/' in cluster_arn else cluster_arn
        task_def   = raw.get('taskDefinitionArn', '')
        task_def_short = task_def.split('task-definition/')[-1] if 'task-definition/' in task_def else task_def
        raw_status = raw.get('lastStatus', 'UNKNOWN')
        try:
            status = Enum__ECS__Task__Status(raw_status)
        except ValueError:
            status = Enum__ECS__Task__Status.UNKNOWN
        resolved_launch_type = launch_type or raw.get('launchType', '')
        if tags is not None:                                                       # caller-supplied dict takes priority
            resolved_tags = tags
        else:                                                                      # fall back to raw list e.g. from describe_tasks
            raw_tags      = raw.get('tags', [])
            resolved_tags = {t['key']: t['value'] for t in raw_tags if 'key' in t}
        eni_id = ''                                                                # extract ENI ID from ElasticNetworkInterface attachment
        for att in (raw.get('attachments') or []):
            if att.get('type') == 'ElasticNetworkInterface':
                for detail in (att.get('details') or []):
                    if detail.get('name') == 'networkInterfaceId':
                        eni_id = detail.get('value', '')
                        break
                if eni_id:
                    break
        return Schema__ECS__Task(
            task_arn        = Safe_Str__ECS__Task__ARN(task_arn) if task_arn.startswith('arn:') else Safe_Str__ECS__Task__ARN(''),
            cluster_name    = Safe_Str__ECS__Cluster__Name(cluster_name) if cluster_name else Safe_Str__ECS__Cluster__Name(''),
            task_definition = Safe_Str__ECS__Task__Definition(task_def_short) if task_def_short else Safe_Str__ECS__Task__Definition(''),
            status          = status,
            last_status     = raw.get('lastStatus', ''),
            desired_status  = raw.get('desiredStatus', ''),
            started_at      = str(raw.get('startedAt', '')) if raw.get('startedAt') else '',
            stopped_at      = str(raw.get('stoppedAt', ''))  if raw.get('stoppedAt')  else '',
            stopped_reason  = raw.get('stoppedReason', ''),
            group           = raw.get('group', ''),
            launch_type     = resolved_launch_type,
            tags            = resolved_tags,
            eni_id          = eni_id,
        )
