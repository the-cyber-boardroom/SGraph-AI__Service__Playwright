# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute_specs vault_app/fargate — Vault_App__Fargate__Cluster__Resolver
# Resolves a cluster name via (1) explicit flag, (2) env var, (3) sole tagged
# cluster auto-discovery, (4) raise ValueError on ambiguity / none found.
# ═══════════════════════════════════════════════════════════════════════════════

import os

from osbot_utils.type_safe.Type_Safe import Type_Safe


_STACK_TAG_VALUE = 'sg-vault-app-fargate'                                       # clusters tagged with this are ours


class Vault_App__Fargate__Cluster__Resolver(Type_Safe):
    fargate_client : object = None                                              # Fargate__AWS__Client injected by caller
    env_var        : str    = 'SG_VAULT_APP__FARGATE__CLUSTER'

    def resolve(self, cluster_flag: str = '') -> str:                           # cluster_flag → env var → auto-discover → raise
        if cluster_flag:                                                         # 1. explicit flag always wins
            return cluster_flag
        env_value = os.environ.get(self.env_var, '')
        if env_value:                                                            # 2. env var if set
            return env_value
        if not self.fargate_client:
            return ''
        clusters   = self.fargate_client.list_clusters()
        candidates = [                                                           # 3. filter to our tagged clusters
            c.cluster_name
            for c in clusters
            if (c.tags or {}).get('Stack') == _STACK_TAG_VALUE
        ]
        if len(candidates) == 1:                                                # exactly one → use it
            return str(candidates[0])
        if len(candidates) == 0:
            raise ValueError('No cluster tagged Stack=sg-vault-app-fargate found in this region')
        raise ValueError(f'Ambiguous cluster: {[str(c) for c in candidates]}')  # 4. multiple → raise
