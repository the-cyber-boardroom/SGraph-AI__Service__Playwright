# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Iam__Graph__Snapshot__Diff
# Diff logic using in-memory writer backed by a tmp directory.
# ═══════════════════════════════════════════════════════════════════════════════

import tempfile

from sgraph_ai_service_playwright__cli.aws.iam.graph.collections.List__Schema__IAM__Graph__Edge import List__Schema__IAM__Graph__Edge
from sgraph_ai_service_playwright__cli.aws.iam.graph.collections.List__Schema__IAM__Graph__Node import List__Schema__IAM__Graph__Node
from sgraph_ai_service_playwright__cli.aws.iam.graph.enums.Enum__IAM__Node__Type               import Enum__IAM__Node__Type
from sgraph_ai_service_playwright__cli.aws.iam.graph.enums.Enum__IAM__Scope__Breadth           import Enum__IAM__Scope__Breadth
from sgraph_ai_service_playwright__cli.aws.iam.graph.primitives.Safe_Str__IAM__Node__Id        import Safe_Str__IAM__Node__Id
from sgraph_ai_service_playwright__cli.aws.iam.graph.schemas.Schema__IAM__Graph__Node          import Schema__IAM__Graph__Node
from sgraph_ai_service_playwright__cli.aws.iam.graph.schemas.Schema__IAM__Graph__Snapshot      import Schema__IAM__Graph__Snapshot
from sgraph_ai_service_playwright__cli.aws.iam.graph.primitives.Safe_Str__IAM__Snapshot__Id    import Safe_Str__IAM__Snapshot__Id
from sgraph_ai_service_playwright__cli.aws.iam.graph.service.Iam__Graph__Builder               import Iam__Graph__Builder
from sgraph_ai_service_playwright__cli.aws.iam.graph.service.Iam__Graph__Vault__Writer         import Iam__Graph__Vault__Writer
from sgraph_ai_service_playwright__cli.aws.iam.graph.service.Iam__Graph__Snapshot__Diff        import Iam__Graph__Snapshot__Diff

_SNAP_A = '2026-01-01T00:00:00Z__aaaaaa'
_SNAP_B = '2026-01-02T00:00:00Z__bbbbbb'


def _node(name: str) -> Schema__IAM__Graph__Node:
    return Schema__IAM__Graph__Node(
        node_id   = Safe_Str__IAM__Node__Id(f'arn:aws:iam::123:role/{name}'),
        node_type = Enum__IAM__Node__Type.ROLE,
        name      = name,
        arn       = f'arn:aws:iam::123:role/{name}',
        scope_breadth = Enum__IAM__Scope__Breadth.SPECIFIC,
    )


def _node_list(*names) -> List__Schema__IAM__Graph__Node:
    lst = List__Schema__IAM__Graph__Node()
    for n in names:
        lst.append(_node(n))
    return lst


def _write_snap(writer, snap_id, *names):
    nodes = _node_list(*names)
    edges = List__Schema__IAM__Graph__Edge()
    meta  = Schema__IAM__Graph__Snapshot(
        snapshot_id = Safe_Str__IAM__Snapshot__Id(snap_id),
        captured_at = '2026-01-01T00:00:00Z',
        role_count  = len(nodes),
    )
    writer.write(snapshot_meta=meta, nodes=nodes, edges=edges)


class Test__Iam__Graph__Snapshot__Diff:

    def test_1__diff_identical_snapshots(self):
        with tempfile.TemporaryDirectory() as tmp:
            writer = Iam__Graph__Vault__Writer(base_path=tmp)
            _write_snap(writer, _SNAP_A, 'role-a', 'role-b')
            _write_snap(writer, _SNAP_B, 'role-a', 'role-b')
            diff = Iam__Graph__Snapshot__Diff(vault_writer=writer).diff(_SNAP_A, _SNAP_B)
            assert diff['added_nodes']   == []
            assert diff['removed_nodes'] == []
            assert diff['node_delta']    == 0

    def test_2__diff_added_role(self):
        with tempfile.TemporaryDirectory() as tmp:
            writer = Iam__Graph__Vault__Writer(base_path=tmp)
            _write_snap(writer, _SNAP_A, 'role-a')
            _write_snap(writer, _SNAP_B, 'role-a', 'role-b')
            diff = Iam__Graph__Snapshot__Diff(vault_writer=writer).diff(_SNAP_A, _SNAP_B)
            assert len(diff['added_nodes']) == 1
            assert diff['added_nodes'][0]['name'] == 'role-b'
            assert diff['node_delta'] == 1

    def test_3__diff_removed_role(self):
        with tempfile.TemporaryDirectory() as tmp:
            writer = Iam__Graph__Vault__Writer(base_path=tmp)
            _write_snap(writer, _SNAP_A, 'role-a', 'role-b')
            _write_snap(writer, _SNAP_B, 'role-a')
            diff = Iam__Graph__Snapshot__Diff(vault_writer=writer).diff(_SNAP_A, _SNAP_B)
            assert len(diff['removed_nodes']) == 1
            assert diff['removed_nodes'][0]['name'] == 'role-b'
            assert diff['node_delta'] == -1

    def test_4__diff_empty_snapshots(self):
        with tempfile.TemporaryDirectory() as tmp:
            writer = Iam__Graph__Vault__Writer(base_path=tmp)
            _write_snap(writer, _SNAP_A)
            _write_snap(writer, _SNAP_B)
            diff = Iam__Graph__Snapshot__Diff(vault_writer=writer).diff(_SNAP_A, _SNAP_B)
            assert diff['node_delta'] == 0
