# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Fargate__AWS__Client__In_Memory
# Dict-backed fake boto3 ECS client for unit tests.  No mocks. No patches.
# Subclasses Fargate__AWS__Client and overrides client() to return _Fake_ECS.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.aws.fargate.service.Fargate__AWS__Client import Fargate__AWS__Client


class _Fake_ECS_Client:
    """Minimal boto3-alike ECS client backed by in-memory dicts."""

    def __init__(self, clusters: dict, task_defs: dict, tasks: dict):
        self._clusters  = clusters   # cluster_name → raw cluster dict
        self._task_defs = task_defs  # task_def_arn → raw task definition dict
        self._tasks     = tasks      # task_arn → raw task dict
        self._td_by_family_rev = {}  # "family:rev" → task_def_arn

    # ── cluster ───────────────────────────────────────────────────────────────

    def list_clusters(self, **kwargs):
        return {'clusterArns': [c['clusterArn'] for c in self._clusters.values()]}

    def describe_clusters(self, clusters: list, include: list = None, **kwargs):
        result = []
        for identifier in clusters:
            raw = self._clusters.get(identifier)             # try by name first
            if raw is None:                                  # then try by ARN suffix
                for candidate in self._clusters.values():
                    if candidate.get('clusterArn') == identifier:
                        raw = candidate
                        break
            if raw:
                result.append(raw)
        return {'clusters': result, 'failures': []}

    def create_cluster(self, clusterName: str, **kwargs):
        arn = f'arn:aws:ecs:us-east-1:123456789012:cluster/{clusterName}'
        raw = {
            'clusterName'       : clusterName,
            'clusterArn'        : arn,
            'status'            : 'ACTIVE',
            'runningTasksCount' : 0,
            'pendingTasksCount' : 0,
            'activeServicesCount': 0,
        }
        self._clusters[clusterName] = raw
        return {'cluster': raw}

    def delete_cluster(self, cluster: str, **kwargs):
        self._clusters.pop(cluster, None)
        return {'cluster': {}}

    # ── task definitions ──────────────────────────────────────────────────────

    def list_task_definitions(self, **kwargs):
        family_prefix = kwargs.get('familyPrefix', '')
        arns = []
        for arn, raw in self._task_defs.items():
            if not family_prefix or raw.get('family', '').startswith(family_prefix):
                arns.append(arn)
        return {'taskDefinitionArns': arns}

    def describe_task_definition(self, taskDefinition: str, **kwargs):
        raw = self._task_defs.get(taskDefinition)
        if raw is None:
            raw = self._td_by_family_rev.get(taskDefinition)
            if raw is None:
                raise Exception(f'ClientError: task definition not found: {taskDefinition}')
        return {'taskDefinition': raw}

    def register_task_definition(self, family: str, cpu: str = '256',
                                  memory: str = '512', **kwargs):
        existing_revs = [
            raw['revision']
            for raw in self._task_defs.values()
            if raw.get('family') == family
        ]
        rev  = (max(existing_revs) + 1) if existing_revs else 1
        arn  = f'arn:aws:ecs:us-east-1:123456789012:task-definition/{family}:{rev}'
        raw  = {
            'family'           : family,
            'revision'         : rev,
            'taskDefinitionArn': arn,
            'status'           : 'ACTIVE',
            'cpu'              : cpu,
            'memory'           : memory,
        }
        self._task_defs[arn] = raw
        self._td_by_family_rev[f'{family}:{rev}'] = raw
        return {'taskDefinition': raw}

    # ── tasks ─────────────────────────────────────────────────────────────────

    def list_tasks(self, **kwargs):
        cluster = kwargs.get('cluster', '')
        family  = kwargs.get('family', '')
        arns    = []
        for arn, raw in self._tasks.items():
            if raw.get('desiredStatus') != 'RUNNING':
                continue
            if cluster and cluster not in raw.get('clusterArn', ''):
                continue
            td_arn = raw.get('taskDefinitionArn', '')
            if family and f'/{family}:' not in td_arn and f'/{family}/' not in td_arn:
                continue
            arns.append(arn)
        return {'taskArns': arns}

    def describe_tasks(self, tasks: list, **kwargs):
        result = []
        for arn in tasks:
            raw = self._tasks.get(arn)
            if raw:
                result.append(raw)
        return {'tasks': result, 'failures': []}

    def run_task(self, cluster: str, taskDefinition: str,
                 count: int = 1, **kwargs):
        import uuid
        task_id  = str(uuid.uuid4())
        task_arn = f'arn:aws:ecs:us-east-1:123456789012:task/{cluster}/{task_id}'
        cluster_arn = f'arn:aws:ecs:us-east-1:123456789012:cluster/{cluster}'
        td_arn   = f'arn:aws:ecs:us-east-1:123456789012:task-definition/{taskDefinition}'
        raw = {
            'taskArn'           : task_arn,
            'clusterArn'        : cluster_arn,
            'taskDefinitionArn' : td_arn,
            'lastStatus'        : 'RUNNING',
            'desiredStatus'     : 'RUNNING',
            'startedAt'         : '2026-05-17T12:00:00',
            'stoppedAt'         : None,
            'stoppedReason'     : '',
            'group'             : '',
        }
        self._tasks[task_arn] = raw
        return {'tasks': [raw], 'failures': []}

    def stop_task(self, task: str, **kwargs):
        raw = self._tasks.get(task)
        if raw:
            raw['lastStatus']    = 'STOPPED'
            raw['desiredStatus'] = 'STOPPED'
        return {'task': raw or {}}


class Fargate__AWS__Client__In_Memory(Fargate__AWS__Client):

    def __init__(self):
        super().__init__()
        self._clusters  = {}
        self._task_defs = {}
        self._tasks     = {}
        self._fake      = _Fake_ECS_Client(self._clusters, self._task_defs, self._tasks)

    def client(self):
        return self._fake
