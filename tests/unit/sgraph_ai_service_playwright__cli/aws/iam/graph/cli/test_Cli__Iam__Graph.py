# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Cli__Iam__Graph
# Tests for sg aws iam graph commands via CliRunner. In-memory writer + orchestrator.
# Critical: `delete --from FILE` without --confirm MUST NOT mutate.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import os
import tempfile
from pathlib import Path

from typer.testing import CliRunner

from sgraph_ai_service_playwright__cli.aws.iam.graph.cli.Cli__Iam__Graph  import graph_app

runner = CliRunner()


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_candidates_file(tmp: str, *names) -> str:
    candidates = [
        dict(node_id=f'arn:aws:iam::123:role/{n}', name=n,
             arn=f'arn:aws:iam::123:role/{n}',
             is_service_linked=False, is_aws_default=False)
        for n in names
    ]
    path = Path(tmp) / 'candidates.json'
    path.write_text(json.dumps({'candidates': candidates}))
    return str(path)


# ── discover ──────────────────────────────────────────────────────────────────

class Test__Cli__Iam__Graph__Discover:

    def test_1__discover_no_real_aws_monkeypatched(self, monkeypatch, tmp_path):
        from sgraph_ai_service_playwright__cli.aws.iam.graph.service.Iam__Discovery__Orchestrator  import Iam__Discovery__Orchestrator
        from sgraph_ai_service_playwright__cli.aws.iam.graph.service.Iam__Graph__Vault__Writer     import Iam__Graph__Vault__Writer
        from sgraph_ai_service_playwright__cli.aws.iam.graph.collections.List__Schema__IAM__Graph__Node import List__Schema__IAM__Graph__Node
        from sgraph_ai_service_playwright__cli.aws.iam.graph.collections.List__Schema__IAM__Graph__Edge import List__Schema__IAM__Graph__Edge
        from tests.unit.sgraph_ai_service_playwright__cli.aws.iam.graph.service.Iam__Discovery__Orchestrator__In_Memory import Iam__Discovery__Orchestrator__In_Memory

        writer = Iam__Graph__Vault__Writer(base_path=str(tmp_path))
        monkeypatch.setattr(
            'sgraph_ai_service_playwright__cli.aws.iam.graph.cli.Cli__Iam__Graph._default_orchestrator',
            lambda: Iam__Discovery__Orchestrator__In_Memory())
        monkeypatch.setattr(
            'sgraph_ai_service_playwright__cli.aws.iam.graph.cli.Cli__Iam__Graph._default_writer',
            lambda: writer)

        result = runner.invoke(graph_app, ['discover', '--json'])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert 'snapshot_id' in data
        assert 'role_count' in data


# ── show ──────────────────────────────────────────────────────────────────────

class Test__Cli__Iam__Graph__Show:

    def test_1__show_no_snapshots(self, monkeypatch, tmp_path):
        from sgraph_ai_service_playwright__cli.aws.iam.graph.service.Iam__Graph__Vault__Writer import Iam__Graph__Vault__Writer
        writer = Iam__Graph__Vault__Writer(base_path=str(tmp_path))
        monkeypatch.setattr(
            'sgraph_ai_service_playwright__cli.aws.iam.graph.cli.Cli__Iam__Graph._default_writer',
            lambda: writer)
        result = runner.invoke(graph_app, ['show'])
        assert result.exit_code == 1

    def test_2__show_existing_snapshot_json(self, monkeypatch, tmp_path):
        from sgraph_ai_service_playwright__cli.aws.iam.graph.service.Iam__Graph__Vault__Writer     import Iam__Graph__Vault__Writer
        from sgraph_ai_service_playwright__cli.aws.iam.graph.collections.List__Schema__IAM__Graph__Node import List__Schema__IAM__Graph__Node
        from sgraph_ai_service_playwright__cli.aws.iam.graph.collections.List__Schema__IAM__Graph__Edge import List__Schema__IAM__Graph__Edge
        from sgraph_ai_service_playwright__cli.aws.iam.graph.schemas.Schema__IAM__Graph__Snapshot  import Schema__IAM__Graph__Snapshot
        from sgraph_ai_service_playwright__cli.aws.iam.graph.primitives.Safe_Str__IAM__Snapshot__Id import Safe_Str__IAM__Snapshot__Id

        writer   = Iam__Graph__Vault__Writer(base_path=str(tmp_path))
        snap_id  = '2026-05-17T10:00:00Z__abc123'
        meta     = Schema__IAM__Graph__Snapshot(
            snapshot_id = Safe_Str__IAM__Snapshot__Id(snap_id),
            captured_at = '2026-05-17T10:00:00+00:00',
            role_count  = 5,
        )
        writer.write(meta, List__Schema__IAM__Graph__Node(), List__Schema__IAM__Graph__Edge())
        monkeypatch.setattr(
            'sgraph_ai_service_playwright__cli.aws.iam.graph.cli.Cli__Iam__Graph._default_writer',
            lambda: writer)

        result = runner.invoke(graph_app, ['show', '--snapshot', snap_id, '--json'])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['role_count'] == 5


# ── filter ────────────────────────────────────────────────────────────────────

class Test__Cli__Iam__Graph__Filter:

    def _write_snapshot_with_roles(self, tmp_path, snap_id, roles):
        from sgraph_ai_service_playwright__cli.aws.iam.graph.service.Iam__Graph__Vault__Writer      import Iam__Graph__Vault__Writer
        from sgraph_ai_service_playwright__cli.aws.iam.graph.collections.List__Schema__IAM__Graph__Node import List__Schema__IAM__Graph__Node
        from sgraph_ai_service_playwright__cli.aws.iam.graph.collections.List__Schema__IAM__Graph__Edge import List__Schema__IAM__Graph__Edge
        from sgraph_ai_service_playwright__cli.aws.iam.graph.schemas.Schema__IAM__Graph__Snapshot   import Schema__IAM__Graph__Snapshot
        from sgraph_ai_service_playwright__cli.aws.iam.graph.schemas.Schema__IAM__Graph__Node       import Schema__IAM__Graph__Node
        from sgraph_ai_service_playwright__cli.aws.iam.graph.primitives.Safe_Str__IAM__Snapshot__Id import Safe_Str__IAM__Snapshot__Id
        from sgraph_ai_service_playwright__cli.aws.iam.graph.primitives.Safe_Str__IAM__Node__Id     import Safe_Str__IAM__Node__Id
        from sgraph_ai_service_playwright__cli.aws.iam.graph.enums.Enum__IAM__Node__Type            import Enum__IAM__Node__Type
        from sgraph_ai_service_playwright__cli.aws.iam.graph.enums.Enum__IAM__Scope__Breadth        import Enum__IAM__Scope__Breadth

        writer = Iam__Graph__Vault__Writer(base_path=str(tmp_path))
        nodes  = List__Schema__IAM__Graph__Node()
        for r in roles:
            nodes.append(Schema__IAM__Graph__Node(
                node_id       = Safe_Str__IAM__Node__Id(f'arn:aws:iam::123:role/{r["name"]}'),
                node_type     = Enum__IAM__Node__Type.ROLE,
                name          = r['name'],
                arn           = f'arn:aws:iam::123:role/{r["name"]}',
                last_used     = r.get('last_used', ''),
                is_aws_default= r.get('is_aws_default', False),
                is_service_linked = r.get('is_service_linked', False),
                scope_breadth = Enum__IAM__Scope__Breadth.SPECIFIC,
            ))
        meta = Schema__IAM__Graph__Snapshot(
            snapshot_id = Safe_Str__IAM__Snapshot__Id(snap_id),
            captured_at = '2026-05-17T00:00:00+00:00',
            role_count  = len(nodes),
        )
        writer.write(meta, nodes, List__Schema__IAM__Graph__Edge())
        return writer

    def test_1__filter_unused_json(self, monkeypatch, tmp_path):
        snap_id = '2026-05-17T10:00:00Z__fff111'
        roles   = [
            {'name': 'sg-stale',  'last_used': '2025-01-01T00:00:00+00:00'},
            {'name': 'sg-recent', 'last_used': '2026-05-10T00:00:00+00:00'},
        ]
        writer = self._write_snapshot_with_roles(tmp_path, snap_id, roles)
        monkeypatch.setattr(
            'sgraph_ai_service_playwright__cli.aws.iam.graph.cli.Cli__Iam__Graph._default_writer',
            lambda: writer)
        result = runner.invoke(graph_app, ['filter', '--unused', '--days', '90',
                                           '--snapshot', snap_id, '--json'])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data['count'] == 1
        assert data['candidates'][0]['name'] == 'sg-stale'

    def test_2__filter_aws_default_json(self, monkeypatch, tmp_path):
        snap_id = '2026-05-17T10:00:01Z__fff222'
        roles   = [
            {'name': 'user-role'},
            {'name': 'AWSServiceRole', 'is_aws_default': True},
        ]
        writer = self._write_snapshot_with_roles(tmp_path, snap_id, roles)
        monkeypatch.setattr(
            'sgraph_ai_service_playwright__cli.aws.iam.graph.cli.Cli__Iam__Graph._default_writer',
            lambda: writer)
        result = runner.invoke(graph_app, ['filter', '--aws-default',
                                           '--snapshot', snap_id, '--json'])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data['count'] == 1
        assert data['candidates'][0]['name'] == 'AWSServiceRole'


# ── delete mutation gate ───────────────────────────────────────────────────────

class Test__Cli__Iam__Graph__Delete:

    def test_1__delete_without_mutation_gate_exits_1(self, monkeypatch, tmp_path):
        monkeypatch.delenv('SG_AWS__IAM__ALLOW_MUTATIONS', raising=False)
        with tempfile.TemporaryDirectory() as tmp:
            cand_file = _make_candidates_file(tmp, 'sg-role')
            result = runner.invoke(graph_app, ['delete', '--from', cand_file])
        assert result.exit_code == 1

    def test_2__delete_without_confirm_is_dry_run(self, monkeypatch, tmp_path):
        monkeypatch.setenv('SG_AWS__IAM__ALLOW_MUTATIONS', '1')
        with tempfile.TemporaryDirectory() as tmp:
            cand_file = _make_candidates_file(tmp, 'sg-role')
            result = runner.invoke(graph_app,
                                   ['delete', '--from', cand_file, '--json'])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data['dry_run'] is True
        assert data['executed'] is False
        assert data['deleted_count'] == 0

    def test_3__delete_with_confirm_and_yes_mutates(self, monkeypatch, tmp_path):
        from tests.unit.sgraph_ai_service_playwright__cli.aws.iam.service.IAM__AWS__Client__In_Memory import IAM__AWS__Client__In_Memory
        from sgraph_ai_service_playwright__cli.aws.iam.graph.service.Iam__Graph__Cleanup              import Iam__Graph__Cleanup
        from sgraph_ai_service_playwright__cli.aws.iam.enums.Enum__IAM__Trust__Service                import Enum__IAM__Trust__Service
        from sgraph_ai_service_playwright__cli.aws.iam.primitives.Safe_Str__IAM__Role_Name            import Safe_Str__IAM__Role_Name
        from sgraph_ai_service_playwright__cli.aws.iam.schemas.Schema__IAM__Role__Create__Request     import Schema__IAM__Role__Create__Request

        monkeypatch.setenv('SG_AWS__IAM__ALLOW_MUTATIONS', '1')

        client = IAM__AWS__Client__In_Memory()
        client.create_role(Schema__IAM__Role__Create__Request(
            role_name    = Safe_Str__IAM__Role_Name('sg-to-delete'),
            trust_service= Enum__IAM__Trust__Service.LAMBDA,
        ))
        cleanup = Iam__Graph__Cleanup(iam_client=client)
        monkeypatch.setattr(
            'sgraph_ai_service_playwright__cli.aws.iam.graph.cli.Cli__Iam__Graph.Iam__Graph__Cleanup',
            lambda: cleanup)

        with tempfile.TemporaryDirectory() as tmp:
            cand_file = _make_candidates_file(tmp, 'sg-to-delete')
            result = runner.invoke(graph_app,
                                   ['delete', '--from', cand_file, '--confirm', '--yes', '--json'])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data['executed'] is True
        assert data['deleted_count'] == 1


# ── snapshots list ─────────────────────────────────────────────────────────────

class Test__Cli__Iam__Graph__Snapshots:

    def test_1__snapshots_list_empty(self, monkeypatch, tmp_path):
        from sgraph_ai_service_playwright__cli.aws.iam.graph.service.Iam__Graph__Vault__Writer import Iam__Graph__Vault__Writer
        writer = Iam__Graph__Vault__Writer(base_path=str(tmp_path))
        monkeypatch.setattr(
            'sgraph_ai_service_playwright__cli.aws.iam.graph.cli.Cli__Iam__Graph._default_writer',
            lambda: writer)
        result = runner.invoke(graph_app, ['snapshots', 'list'])
        assert result.exit_code == 0
        assert 'No snapshots' in result.output
