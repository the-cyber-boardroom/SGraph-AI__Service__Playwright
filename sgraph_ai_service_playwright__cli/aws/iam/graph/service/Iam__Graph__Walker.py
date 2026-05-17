# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Iam__Graph__Walker
# Transitive permission walk starting from a root node (role ARN or name).
# Follows MANAGED_POLICY and INLINE_POLICY edges up to --depth hops.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                            import Type_Safe

from sgraph_ai_service_playwright__cli.aws.iam.graph.collections.List__Schema__IAM__Graph__Edge import List__Schema__IAM__Graph__Edge
from sgraph_ai_service_playwright__cli.aws.iam.graph.collections.List__Schema__IAM__Graph__Node import List__Schema__IAM__Graph__Node


class Iam__Graph__Walker(Type_Safe):

    # ── public ────────────────────────────────────────────────────────────────

    def walk(self,
             root_id    : str,
             nodes      : list,                                                  # list of node dicts (from vault)
             edges      : list,                                                  # list of edge dicts (from vault)
             max_depth  : int = 3) -> dict:
        node_map = {n['node_id']: n for n in nodes}
        adjacency = {}                                                           # node_id → list of target_id
        for e in edges:
            src = e.get('source_id', '')
            tgt = e.get('target_id', '')
            if src not in adjacency:
                adjacency[src] = []
            adjacency[src].append(tgt)

        visited  = {}                                                            # node_id → depth first reached
        frontier = [(root_id, 0)]
        while frontier:
            current_id, depth = frontier.pop(0)
            if current_id in visited:
                continue
            visited[current_id] = depth
            if depth >= max_depth:
                continue
            for target_id in adjacency.get(current_id, []):
                if target_id not in visited:
                    frontier.append((target_id, depth + 1))

        walk_nodes = []
        for node_id, depth in visited.items():
            node = node_map.get(node_id, {'node_id': node_id, 'name': node_id})
            walk_nodes.append(dict(**node, walk_depth=depth))
        walk_nodes.sort(key=lambda n: n['walk_depth'])

        return dict(
            root       = root_id,
            max_depth  = max_depth,
            node_count = len(walk_nodes),
            nodes      = walk_nodes,
        )
