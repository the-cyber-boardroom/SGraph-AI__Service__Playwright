# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Fargate__AWS__Client (via in-memory fake)
# ═══════════════════════════════════════════════════════════════════════════════

import pytest

from sgraph_ai_service_playwright__cli.aws.fargate.enums.Enum__ECS__Task__Status import Enum__ECS__Task__Status
from tests.unit.sgraph_ai_service_playwright__cli.aws.fargate.service.Fargate__AWS__Client__In_Memory import Fargate__AWS__Client__In_Memory


def _client() -> Fargate__AWS__Client__In_Memory:
    return Fargate__AWS__Client__In_Memory()


class Test__Fargate__AWS__Client:

    # ── cluster read ──────────────────────────────────────────────────────────

    def test_1__list_clusters_empty(self):
        clusters = list(_client().list_clusters())
        assert clusters == []

    def test_2__create_cluster_and_list(self):
        c = _client()
        cluster = c.create_cluster('my-cluster')
        assert str(cluster.cluster_name) == 'my-cluster'
        assert cluster.status == 'ACTIVE'
        listed = list(c.list_clusters())
        assert len(listed) == 1
        assert str(listed[0].cluster_name) == 'my-cluster'

    def test_3__describe_cluster_existing(self):
        c = _client()
        c.create_cluster('sg-test')
        desc = c.describe_cluster('sg-test')
        assert desc is not None
        assert str(desc.cluster_name) == 'sg-test'
        assert 'arn:aws:ecs' in desc.cluster_arn

    def test_4__describe_cluster_missing_returns_none(self):
        assert _client().describe_cluster('no-such-cluster') is None

    def test_5__delete_cluster(self):
        c = _client()
        c.create_cluster('to-delete')
        c.delete_cluster('to-delete')
        assert c.describe_cluster('to-delete') is None

    def test_6__delete_cluster_with_running_tasks_raises(self):
        c = _client()
        c.create_cluster('busy-cluster')
        # manually inject a running task count into the fake
        c._fake._clusters['busy-cluster']['runningTasksCount'] = 2
        with pytest.raises(ValueError, match='running tasks'):
            c.delete_cluster('busy-cluster')

    # ── task-def ──────────────────────────────────────────────────────────────

    def test_7__list_task_definitions_empty(self):
        tds = list(_client().list_task_definitions())
        assert tds == []

    def test_8__register_and_list_task_definition(self):
        c  = _client()
        td = c.register_task_definition(name='hello-world', image='hello:latest',
                                         cpu='256', memory='512')
        assert td is not None
        assert td.family   == 'hello-world'
        assert td.revision == 1
        assert td.cpu      == '256'
        listed = list(c.list_task_definitions())
        assert len(listed) == 1

    def test_9__register_increments_revision(self):
        c   = _client()
        td1 = c.register_task_definition('my-task', 'img:1')
        td2 = c.register_task_definition('my-task', 'img:2')
        assert td1.revision == 1
        assert td2.revision == 2

    def test_10__describe_task_definition(self):
        c  = _client()
        c.register_task_definition('my-task', 'img:latest')
        td = c.describe_task_definition('my-task:1')
        assert td is not None
        assert td.family == 'my-task'

    def test_11__list_task_definitions_family_filter(self):
        c = _client()
        c.register_task_definition('app-a', 'img:a')
        c.register_task_definition('app-b', 'img:b')
        c.register_task_definition('svc-x', 'img:x')
        result = list(c.list_task_definitions(family='app'))
        assert len(result) == 2

    # ── task ──────────────────────────────────────────────────────────────────

    def test_12__list_tasks_empty(self):
        tasks = list(_client().list_tasks(cluster='my-cluster'))
        assert tasks == []

    def test_13__run_task_and_list(self):
        c = _client()
        c.create_cluster('sg-cluster')
        c.register_task_definition('hello-world', 'hello:latest')
        task = c.run_task(cluster='sg-cluster', task_def='hello-world:1')
        assert task is not None
        assert str(task.status) == 'RUNNING'
        listed = list(c.list_tasks(cluster='sg-cluster'))
        assert len(listed) == 1

    def test_14__describe_task(self):
        c = _client()
        c.create_cluster('sg-cluster')
        c.register_task_definition('hello-world', 'hello:latest')
        task = c.run_task(cluster='sg-cluster', task_def='hello-world:1')
        arn  = str(task.task_arn)
        described = c.describe_task(arn, cluster='sg-cluster')
        assert described is not None
        assert str(described.task_arn) == arn

    def test_15__stop_task(self):
        c = _client()
        c.create_cluster('sg-cluster')
        c.register_task_definition('hello-world', 'hello:latest')
        task = c.run_task(cluster='sg-cluster', task_def='hello-world:1')
        arn  = str(task.task_arn)
        c.stop_task(arn)
        desc = c.describe_task(arn)
        assert str(desc.status) == 'STOPPED'

    # ── new-field round-trips ─────────────────────────────────────────────────

    def test_16__register_task_def_with_port_mappings(self):
        c  = _client()
        td = c.register_task_definition(
            name='vault-app', image='123.dkr.ecr.us-east-1.amazonaws.com/vault:latest',
            port_mappings=[{'containerPort': 8080, 'protocol': 'tcp'},
                           {'containerPort': 443,  'protocol': 'tcp'}])
        assert td is not None
        pms = list(td.port_mappings)
        assert len(pms) == 2
        assert pms[0].container_port == 8080
        assert pms[0].protocol       == 'tcp'
        assert pms[1].container_port == 443

    def test_17__register_task_def_with_execution_role(self):
        c  = _client()
        td = c.register_task_definition(
            name='vault-app', image='hello:latest',
            execution_role_arn='arn:aws:iam::123456789012:role/ecsTaskExecutionRole',
            task_role_arn='arn:aws:iam::123456789012:role/myTaskRole')
        assert td.execution_role_arn == 'arn:aws:iam::123456789012:role/ecsTaskExecutionRole'
        assert td.task_role_arn      == 'arn:aws:iam::123456789012:role/myTaskRole'

    def test_18__register_task_def_with_log_group(self):
        c  = _client()
        td = c.register_task_definition(
            name='vault-app', image='hello:latest',
            log_group='/ecs/vault')
        assert td.log_group == '/ecs/vault'

    def test_19__register_task_def_default_log_group(self):
        c  = _client()
        td = c.register_task_definition(name='my-task', image='hello:latest')
        assert td.log_group == '/ecs/my-task'                                     # convention: /ecs/<family>

    def test_20__run_task_with_launch_type(self):
        c = _client()
        c.create_cluster('sg-cluster')
        c.register_task_definition('hello-world', 'hello:latest')
        task = c.run_task(cluster='sg-cluster', task_def='hello-world:1',
                          launch_type='FARGATE_SPOT')
        assert task is not None
        assert task.launch_type == 'FARGATE_SPOT'

    def test_21__run_task_with_tags(self):
        c = _client()
        c.create_cluster('sg-cluster')
        c.register_task_definition('hello-world', 'hello:latest')
        task = c.run_task(cluster='sg-cluster', task_def='hello-world:1',
                          tags={'env': 'prod', 'owner': 'platform'})
        assert task is not None
        assert task.tags.get('env')   == 'prod'
        assert task.tags.get('owner') == 'platform'

    def test_22__run_task_default_launch_type_is_fargate(self):
        c = _client()
        c.create_cluster('sg-cluster')
        c.register_task_definition('hello-world', 'hello:latest')
        task = c.run_task(cluster='sg-cluster', task_def='hello-world:1')
        assert task.launch_type == 'FARGATE'
