# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Cli__Fargate
# Tests for sg aws fargate cluster / task-def / task via CliRunner.
# Mutations are exercised with SG_AWS__FARGATE__ALLOW_MUTATIONS=1 in env.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import os

import pytest
from typer.testing import CliRunner

from sgraph_ai_service_playwright__cli.aws.fargate.cli.Cli__Fargate import app
from tests.unit.sgraph_ai_service_playwright__cli.aws.fargate.service.Fargate__AWS__Client__In_Memory import Fargate__AWS__Client__In_Memory

runner = CliRunner()

_MUTATION_ENV = 'SG_AWS__FARGATE__ALLOW_MUTATIONS'


def _seed_client(client: Fargate__AWS__Client__In_Memory):
    client.create_cluster('sg-test-cluster')
    client.register_task_definition('hello-world', 'hello:latest', cpu='256', memory='512')
    client.run_task(cluster='sg-test-cluster', task_def='hello-world:1')
    return client


class Test__Cli__Fargate__Cluster:

    def test_1__cluster_list_empty(self, monkeypatch):
        client = Fargate__AWS__Client__In_Memory()
        monkeypatch.setattr('sgraph_ai_service_playwright__cli.aws.fargate.cli.Cli__Fargate._client',
                            lambda: client)
        result = runner.invoke(app, ['cluster', 'list'])
        assert result.exit_code == 0
        assert 'No ECS clusters' in result.output

    def test_2__cluster_list_json(self, monkeypatch):
        client = _seed_client(Fargate__AWS__Client__In_Memory())
        monkeypatch.setattr('sgraph_ai_service_playwright__cli.aws.fargate.cli.Cli__Fargate._client',
                            lambda: client)
        result = runner.invoke(app, ['cluster', 'list', '--json'])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]['cluster_name'] == 'sg-test-cluster'

    def test_3__cluster_describe_existing_json(self, monkeypatch):
        client = _seed_client(Fargate__AWS__Client__In_Memory())
        monkeypatch.setattr('sgraph_ai_service_playwright__cli.aws.fargate.cli.Cli__Fargate._client',
                            lambda: client)
        result = runner.invoke(app, ['cluster', 'describe', 'sg-test-cluster', '--json'])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['cluster_name'] == 'sg-test-cluster'
        assert data['status'] == 'ACTIVE'

    def test_4__cluster_describe_missing(self, monkeypatch):
        client = Fargate__AWS__Client__In_Memory()
        monkeypatch.setattr('sgraph_ai_service_playwright__cli.aws.fargate.cli.Cli__Fargate._client',
                            lambda: client)
        result = runner.invoke(app, ['cluster', 'describe', 'no-such-cluster'])
        assert result.exit_code == 1

    def test_5__cluster_create_requires_mutation_gate(self, monkeypatch):
        monkeypatch.delenv(_MUTATION_ENV, raising=False)
        result = runner.invoke(app, ['cluster', 'create', 'new-cluster', '--yes'])
        assert result.exit_code == 1
        assert _MUTATION_ENV in result.output

    def test_6__cluster_create_with_gate(self, monkeypatch):
        client = Fargate__AWS__Client__In_Memory()
        monkeypatch.setenv(_MUTATION_ENV, '1')
        monkeypatch.setattr('sgraph_ai_service_playwright__cli.aws.fargate.cli.Cli__Fargate._client',
                            lambda: client)
        result = runner.invoke(app, ['cluster', 'create', 'new-cluster', '--yes', '--json'])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['cluster_name'] == 'new-cluster'

    def test_7__cluster_delete_requires_mutation_gate(self, monkeypatch):
        monkeypatch.delenv(_MUTATION_ENV, raising=False)
        result = runner.invoke(app, ['cluster', 'delete', 'some-cluster', '--yes'])
        assert result.exit_code == 1

    def test_8__cluster_delete_with_gate(self, monkeypatch):
        client = _seed_client(Fargate__AWS__Client__In_Memory())
        # stop the running task first to allow deletion
        for arn in list(client._tasks.keys()):
            client._tasks[arn]['desiredStatus'] = 'STOPPED'
        monkeypatch.setenv(_MUTATION_ENV, '1')
        monkeypatch.setattr('sgraph_ai_service_playwright__cli.aws.fargate.cli.Cli__Fargate._client',
                            lambda: client)
        result = runner.invoke(app, ['cluster', 'delete', 'sg-test-cluster', '--yes'])
        assert result.exit_code == 0


class Test__Cli__Fargate__TaskDef:

    def test_1__task_def_list_empty(self, monkeypatch):
        client = Fargate__AWS__Client__In_Memory()
        monkeypatch.setattr('sgraph_ai_service_playwright__cli.aws.fargate.cli.Cli__Fargate._client',
                            lambda: client)
        result = runner.invoke(app, ['task-def', 'list'])
        assert result.exit_code == 0
        assert 'No task definitions' in result.output

    def test_2__task_def_list_json(self, monkeypatch):
        client = _seed_client(Fargate__AWS__Client__In_Memory())
        monkeypatch.setattr('sgraph_ai_service_playwright__cli.aws.fargate.cli.Cli__Fargate._client',
                            lambda: client)
        result = runner.invoke(app, ['task-def', 'list', '--json'])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]['family'] == 'hello-world'

    def test_3__task_def_show_json(self, monkeypatch):
        client = _seed_client(Fargate__AWS__Client__In_Memory())
        monkeypatch.setattr('sgraph_ai_service_playwright__cli.aws.fargate.cli.Cli__Fargate._client',
                            lambda: client)
        result = runner.invoke(app, ['task-def', 'show', 'hello-world:1', '--json'])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['family']   == 'hello-world'
        assert data['revision'] == 1

    def test_4__task_def_register_requires_mutation_gate(self, monkeypatch):
        monkeypatch.delenv(_MUTATION_ENV, raising=False)
        result = runner.invoke(app, ['task-def', 'register',
                                     '--name', 'my-task', '--image', 'img:latest', '--yes'])
        assert result.exit_code == 1

    def test_5__task_def_register_with_gate(self, monkeypatch):
        client = Fargate__AWS__Client__In_Memory()
        monkeypatch.setenv(_MUTATION_ENV, '1')
        monkeypatch.setattr('sgraph_ai_service_playwright__cli.aws.fargate.cli.Cli__Fargate._client',
                            lambda: client)
        result = runner.invoke(app, ['task-def', 'register',
                                     '--name', 'my-task', '--image', 'img:latest',
                                     '--yes', '--json'])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['family']   == 'my-task'
        assert data['revision'] == 1


class Test__Cli__Fargate__Task:

    def test_1__task_list_empty(self, monkeypatch):
        client = Fargate__AWS__Client__In_Memory()
        monkeypatch.setattr('sgraph_ai_service_playwright__cli.aws.fargate.cli.Cli__Fargate._client',
                            lambda: client)
        result = runner.invoke(app, ['task', 'list'])
        assert result.exit_code == 0
        assert 'No running tasks' in result.output

    def test_2__task_list_json(self, monkeypatch):
        client = _seed_client(Fargate__AWS__Client__In_Memory())
        monkeypatch.setattr('sgraph_ai_service_playwright__cli.aws.fargate.cli.Cli__Fargate._client',
                            lambda: client)
        result = runner.invoke(app, ['task', 'list', '--cluster', 'sg-test-cluster', '--json'])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1
        assert 'arn:aws:ecs' in data[0]['task_arn']

    def test_3__task_describe_json(self, monkeypatch):
        client = _seed_client(Fargate__AWS__Client__In_Memory())
        task_arns = list(client._tasks.keys())
        arn = task_arns[0]
        monkeypatch.setattr('sgraph_ai_service_playwright__cli.aws.fargate.cli.Cli__Fargate._client',
                            lambda: client)
        result = runner.invoke(app, ['task', 'describe', arn, '--json'])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['task_arn'] == arn

    def test_4__task_run_requires_mutation_gate(self, monkeypatch):
        monkeypatch.delenv(_MUTATION_ENV, raising=False)
        result = runner.invoke(app, ['task', 'run',
                                     '--cluster', 'sg-cluster', '--task-def', 'hello-world:1', '--yes'])
        assert result.exit_code == 1

    def test_5__task_run_with_gate(self, monkeypatch):
        client = _seed_client(Fargate__AWS__Client__In_Memory())
        monkeypatch.setenv(_MUTATION_ENV, '1')
        monkeypatch.setattr('sgraph_ai_service_playwright__cli.aws.fargate.cli.Cli__Fargate._client',
                            lambda: client)
        result = runner.invoke(app, ['task', 'run',
                                     '--cluster', 'sg-test-cluster', '--task-def', 'hello-world:1',
                                     '--yes', '--json'])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert 'arn:aws:ecs' in data['task_arn']
        assert data['status'] == 'RUNNING'

    def test_6__task_stop_requires_mutation_gate(self, monkeypatch):
        monkeypatch.delenv(_MUTATION_ENV, raising=False)
        result = runner.invoke(app, ['task', 'stop',
                                     'arn:aws:ecs:us-east-1:123456789012:task/cluster/abc', '--yes'])
        assert result.exit_code == 1

    def test_7__task_stop_with_gate(self, monkeypatch):
        client   = _seed_client(Fargate__AWS__Client__In_Memory())
        task_arn = list(client._tasks.keys())[0]
        monkeypatch.setenv(_MUTATION_ENV, '1')
        monkeypatch.setattr('sgraph_ai_service_playwright__cli.aws.fargate.cli.Cli__Fargate._client',
                            lambda: client)
        result = runner.invoke(app, ['task', 'stop', task_arn, '--yes'])
        assert result.exit_code == 0
        assert 'Stopped' in result.output
