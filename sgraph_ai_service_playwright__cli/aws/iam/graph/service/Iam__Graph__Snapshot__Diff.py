# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Iam__Graph__Snapshot__Diff
# Computes a structural diff between two IAM graph snapshots.
# Returns added / removed / changed node names (by node_id key).
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                      import Type_Safe

from sgraph_ai_service_playwright__cli.aws.iam.graph.service.Iam__Graph__Vault__Writer   import Iam__Graph__Vault__Writer


class Iam__Graph__Snapshot__Diff(Type_Safe):

    vault_writer : Iam__Graph__Vault__Writer

    def setup(self):
        if self.vault_writer is None:
            self.vault_writer = Iam__Graph__Vault__Writer()
        return self

    # ── public ────────────────────────────────────────────────────────────────

    def diff(self, snapshot_a: str, snapshot_b: str) -> dict:
        self.setup()
        nodes_a = {n['node_id']: n for n in self.vault_writer.load_nodes(snapshot_a)}
        nodes_b = {n['node_id']: n for n in self.vault_writer.load_nodes(snapshot_b)}
        edges_a = {(e['source_id'], e['target_id']): e for e in self.vault_writer.load_edges(snapshot_a)}
        edges_b = {(e['source_id'], e['target_id']): e for e in self.vault_writer.load_edges(snapshot_b)}

        added_nodes   = [nodes_b[k] for k in set(nodes_b) - set(nodes_a)]
        removed_nodes = [nodes_a[k] for k in set(nodes_a) - set(nodes_b)]
        added_edges   = [edges_b[k] for k in set(edges_b) - set(edges_a)]
        removed_edges = [edges_a[k] for k in set(edges_a) - set(edges_b)]

        return dict(
            snapshot_a     = snapshot_a,
            snapshot_b     = snapshot_b,
            added_nodes    = added_nodes,
            removed_nodes  = removed_nodes,
            added_edges    = added_edges,
            removed_edges  = removed_edges,
            node_delta     = len(added_nodes) - len(removed_nodes),
            edge_delta     = len(added_edges) - len(removed_edges),
        )
