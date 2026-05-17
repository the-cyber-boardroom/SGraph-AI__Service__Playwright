# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Iam__Graph__Vault__Writer
# Writes an IAM graph snapshot to ~/.sg/aws/iam-graph/<snapshot-id>/.
# Directory: 0700. Files: 0600. One JSON file per role/policy/user/group.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import os
from pathlib import Path

from osbot_utils.type_safe.Type_Safe                                                            import Type_Safe

from sgraph_ai_service_playwright__cli.aws.iam.graph.collections.List__Schema__IAM__Graph__Edge import List__Schema__IAM__Graph__Edge
from sgraph_ai_service_playwright__cli.aws.iam.graph.collections.List__Schema__IAM__Graph__Node import List__Schema__IAM__Graph__Node
from sgraph_ai_service_playwright__cli.aws.iam.graph.enums.Enum__IAM__Node__Type               import Enum__IAM__Node__Type
from sgraph_ai_service_playwright__cli.aws.iam.graph.schemas.Schema__IAM__Graph__Snapshot      import Schema__IAM__Graph__Snapshot
from sgraph_ai_service_playwright__cli.aws.iam.graph.service.Iam__Graph__Builder               import Iam__Graph__Builder

_VAULT_BASE  = str(Path.home() / '.sg' / 'aws' / 'iam-graph')
_DIR_MODE    = 0o700
_FILE_MODE   = 0o600

_NODE_TYPE_FOLDER = {
    Enum__IAM__Node__Type.ROLE  : 'roles',
    Enum__IAM__Node__Type.POLICY: 'policies',
    Enum__IAM__Node__Type.USER  : 'users',
    Enum__IAM__Node__Type.GROUP : 'groups',
}


class Iam__Graph__Vault__Writer(Type_Safe):

    base_path : str = _VAULT_BASE                                                # override in tests; str not Path (Type_Safe constraint)

    # ── property ──────────────────────────────────────────────────────────────

    def base_path_as_path(self) -> Path:
        return Path(self.base_path)

    # ── public ────────────────────────────────────────────────────────────────

    def write(self,
              snapshot_meta  : Schema__IAM__Graph__Snapshot,
              nodes          : List__Schema__IAM__Graph__Node,
              edges          : List__Schema__IAM__Graph__Edge) -> Path:
        snap_dir = self.ensure_snap_dir(str(snapshot_meta.snapshot_id))
        builder  = Iam__Graph__Builder()

        # ── per-node files ────────────────────────────────────────────────────
        for node in nodes:
            folder   = _NODE_TYPE_FOLDER.get(node.node_type, 'other')
            node_dir = snap_dir / folder
            node_dir.mkdir(mode=_DIR_MODE, exist_ok=True)
            safe_name = (node.name or str(node.node_id)).replace('/', '__')
            file_path = node_dir / f'{safe_name}.json'
            payload   = dict(
                node_id           = str(node.node_id),
                node_type         = str(node.node_type),
                name              = node.name,
                arn               = node.arn,
                created_at        = node.created_at,
                last_used         = node.last_used,
                scope_breadth     = str(node.scope_breadth),
                is_aws_default    = node.is_aws_default,
                is_service_linked = node.is_service_linked,
                trust_principal   = node.trust_principal,
                tags_json         = node.tags_json,
            )
            self.write_file(file_path, payload)

        # ── edges.json ────────────────────────────────────────────────────────
        edges_path = snap_dir / 'edges.json'
        self.write_file(edges_path, builder.edges_to_dict_list(edges))

        # ── snapshot.json ─────────────────────────────────────────────────────
        snap_path = snap_dir / 'snapshot.json'
        self.write_file(snap_path, dict(
            snapshot_id    = str(snapshot_meta.snapshot_id),
            captured_at    = snapshot_meta.captured_at,
            role_count     = snapshot_meta.role_count,
            policy_count   = snapshot_meta.policy_count,
            user_count     = snapshot_meta.user_count,
            group_count    = snapshot_meta.group_count,
            edge_count     = snapshot_meta.edge_count,
            aws_account_id = snapshot_meta.aws_account_id,
            region         = snapshot_meta.region,
        ))

        return snap_dir

    def list_snapshots(self) -> list:
        base = self.base_path_as_path()
        if not base.exists():
            return []
        result = []
        for entry in sorted(base.iterdir(), reverse=True):
            if not entry.is_dir():
                continue
            snap_file = entry / 'snapshot.json'
            if not snap_file.exists():
                continue
            try:
                data = json.loads(snap_file.read_text())
                result.append(data)
            except Exception:
                continue
        return result

    def load_snapshot(self, snapshot_id: str) -> dict:
        snap_dir  = self.base_path_as_path() / snapshot_id
        snap_file = snap_dir / 'snapshot.json'
        if not snap_file.exists():
            return {}
        return json.loads(snap_file.read_text())

    def load_nodes(self, snapshot_id: str) -> list:
        snap_dir = self.base_path_as_path() / snapshot_id
        nodes    = []
        for folder in ('roles', 'policies', 'users', 'groups'):
            folder_path = snap_dir / folder
            if not folder_path.exists():
                continue
            for f in sorted(folder_path.iterdir()):
                if f.suffix == '.json':
                    try:
                        nodes.append(json.loads(f.read_text()))
                    except Exception:
                        continue
        return nodes

    def load_edges(self, snapshot_id: str) -> list:
        edges_file = self.base_path_as_path() / snapshot_id / 'edges.json'
        if not edges_file.exists():
            return []
        return json.loads(edges_file.read_text())

    def latest_snapshot_id(self) -> str:
        snaps = self.list_snapshots()
        if not snaps:
            return ''
        return snaps[0].get('snapshot_id', '')

    # ── internal ──────────────────────────────────────────────────────────────

    def ensure_snap_dir(self, snapshot_id: str) -> Path:
        snap_dir = self.base_path_as_path() / snapshot_id
        snap_dir.mkdir(parents=True, mode=_DIR_MODE, exist_ok=True)
        os.chmod(snap_dir, _DIR_MODE)
        return snap_dir

    def write_file(self, path: Path, data) -> None:
        text = json.dumps(data, indent=2, default=str)
        path.write_text(text)
        os.chmod(path, _FILE_MODE)
