# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute_specs vault_app/fargate — Vault_App__Fargate__Slug__Resolver
# Resolves a running vault slug within a cluster.  Slug uniqueness is
# per-cluster: two clusters may each have a 'dinis-tue' slug.
# check_unique() is the collision guard called by start before run_task.
# ═══════════════════════════════════════════════════════════════════════════════

from typing import Any

from osbot_utils.type_safe.Type_Safe import Type_Safe


_SLUG_TAG = 'VaultApp__Slug'                                                    # tag key on every running vault task


class Vault_App__Fargate__Slug__Resolver(Type_Safe):
    fargate_client : Any    = None                                              # Fargate__AWS__Client injected by caller

    def _running_slug_tasks(self, cluster_name: str) -> list:                  # returns list of (slug, task_arn) for RUNNING tasks
        if not self.fargate_client:
            return []
        tasks = self.fargate_client.list_tasks(cluster=cluster_name)
        result = []
        for task in tasks:
            slug = (task.tags or {}).get(_SLUG_TAG, '')
            if slug:
                result.append((slug, str(task.task_arn)))
        return result

    def resolve(self, cluster_name: str, slug_flag: str = '') -> str:          # slug_flag → sole running task → raise
        pairs = self._running_slug_tasks(cluster_name)
        if slug_flag:                                                           # 1. explicit slug — verify it exists
            matches = [arn for slug, arn in pairs if slug == slug_flag]
            if not matches:
                raise ValueError(
                    f'No RUNNING task with {_SLUG_TAG}={slug_flag!r} '
                    f'found in cluster {cluster_name!r}'
                )
            return slug_flag
        if len(pairs) == 1:                                                    # 2. exactly one running slug
            return pairs[0][0]
        if len(pairs) == 0:
            raise ValueError(
                f'No RUNNING tasks with {_SLUG_TAG} tag found '
                f'in cluster {cluster_name!r}'
            )
        candidates = [slug for slug, _ in pairs]
        raise ValueError(f'Ambiguous slug: {candidates}')                      # 3. multiple → raise

    def check_unique(self, cluster_name: str, slug: str) -> None:              # called by start; raises on collision
        pairs = self._running_slug_tasks(cluster_name)
        if any(s == slug for s, _ in pairs):
            raise ValueError(
                f'Slug {slug!r} already running in cluster {cluster_name!r}'
            )
