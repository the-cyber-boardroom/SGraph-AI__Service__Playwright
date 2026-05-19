# ═══════════════════════════════════════════════════════════════════════════════
# tests/unit — test_Vault_App__Fargate__Resolvers
# Covers: Cluster__Resolver and Slug__Resolver using in-memory fargate client.
# ═══════════════════════════════════════════════════════════════════════════════

import os
from unittest import TestCase

from sg_compute_specs.vault_app.fargate.service.Vault_App__Fargate__Cluster__Resolver import Vault_App__Fargate__Cluster__Resolver
from sg_compute_specs.vault_app.fargate.service.Vault_App__Fargate__Slug__Resolver    import Vault_App__Fargate__Slug__Resolver
from tests.unit.sgraph_ai_service_playwright__cli.aws.fargate.service.Fargate__AWS__Client__In_Memory import (
    Fargate__AWS__Client__In_Memory,
)

_OUR_STACK_TAG = {'Stack': 'sg-vault-app-fargate'}


class test_Vault_App__Fargate__Cluster__Resolver(TestCase):

    def setUp(self):
        self.fargate  = Fargate__AWS__Client__In_Memory()
        self.resolver = Vault_App__Fargate__Cluster__Resolver(fargate_client=self.fargate)

    def tearDown(self):
        os.environ.pop('SG_VAULT_APP__FARGATE__CLUSTER', None)                 # clean env after each test

    # ── explicit flag ────────────────────────────────────────────────────────

    def test_explicit_flag_wins_over_env(self):
        os.environ['SG_VAULT_APP__FARGATE__CLUSTER'] = 'env-cluster'
        result = self.resolver.resolve(cluster_flag='flag-cluster')
        assert result == 'flag-cluster'

    def test_explicit_flag_wins_over_auto_discover(self):
        self.fargate.seed_cluster_with_tags('auto-cluster', _OUR_STACK_TAG)
        result = self.resolver.resolve(cluster_flag='explicit-cluster')
        assert result == 'explicit-cluster'

    # ── env var ──────────────────────────────────────────────────────────────

    def test_env_var_used_when_no_flag(self):
        os.environ['SG_VAULT_APP__FARGATE__CLUSTER'] = 'env-cluster'
        result = self.resolver.resolve()
        assert result == 'env-cluster'

    def test_env_var_used_over_auto_discover(self):
        os.environ['SG_VAULT_APP__FARGATE__CLUSTER'] = 'env-cluster'
        self.fargate.seed_cluster_with_tags('auto-cluster', _OUR_STACK_TAG)
        result = self.resolver.resolve()
        assert result == 'env-cluster'

    # ── auto-discovery ───────────────────────────────────────────────────────

    def test_sole_tagged_cluster_auto_resolved(self):
        self.fargate.seed_cluster_with_tags('sole-cluster', _OUR_STACK_TAG)
        result = self.resolver.resolve()
        assert result == 'sole-cluster'

    def test_untagged_clusters_ignored_in_auto_discover(self):
        self.fargate.seed_cluster_with_tags('other-cluster', {'Stack': 'something-else'})
        self.fargate.seed_cluster_with_tags('our-cluster', _OUR_STACK_TAG)
        result = self.resolver.resolve()
        assert result == 'our-cluster'

    # ── error cases ──────────────────────────────────────────────────────────

    def test_raises_on_no_tagged_clusters(self):
        with self.assertRaises(ValueError):
            self.resolver.resolve()

    def test_raises_on_multiple_tagged_clusters(self):
        self.fargate.seed_cluster_with_tags('cluster-a', _OUR_STACK_TAG)
        self.fargate.seed_cluster_with_tags('cluster-b', _OUR_STACK_TAG)
        with self.assertRaises(ValueError) as ctx:
            self.resolver.resolve()
        assert 'Ambiguous' in str(ctx.exception)

    def test_ambiguity_error_lists_candidates(self):
        self.fargate.seed_cluster_with_tags('cluster-a', _OUR_STACK_TAG)
        self.fargate.seed_cluster_with_tags('cluster-b', _OUR_STACK_TAG)
        with self.assertRaises(ValueError) as ctx:
            self.resolver.resolve()
        msg = str(ctx.exception)
        assert 'cluster-a' in msg and 'cluster-b' in msg


class test_Vault_App__Fargate__Slug__Resolver(TestCase):

    def setUp(self):
        self.fargate  = Fargate__AWS__Client__In_Memory()
        self.resolver = Vault_App__Fargate__Slug__Resolver(fargate_client=self.fargate)

    # ── explicit slug flag ───────────────────────────────────────────────────

    def test_explicit_slug_verified_against_running_tasks(self):
        self.fargate.seed_cluster_with_tags('my-cluster', _OUR_STACK_TAG)
        self.fargate.seed_task_with_tags('my-cluster', {'VaultApp__Slug': 'dinis-tue'})
        result = self.resolver.resolve('my-cluster', slug_flag='dinis-tue')
        assert result == 'dinis-tue'

    def test_explicit_slug_raises_when_not_running(self):
        self.fargate.seed_cluster_with_tags('my-cluster', _OUR_STACK_TAG)
        with self.assertRaises(ValueError):
            self.resolver.resolve('my-cluster', slug_flag='ghost-slug')

    # ── auto slug resolution ─────────────────────────────────────────────────

    def test_sole_running_slug_auto_resolved(self):
        self.fargate.seed_cluster_with_tags('my-cluster', _OUR_STACK_TAG)
        self.fargate.seed_task_with_tags('my-cluster', {'VaultApp__Slug': 'dinis-tue'})
        result = self.resolver.resolve('my-cluster')
        assert result == 'dinis-tue'

    def test_raises_when_no_running_tasks(self):
        self.fargate.seed_cluster_with_tags('my-cluster', _OUR_STACK_TAG)
        with self.assertRaises(ValueError):
            self.resolver.resolve('my-cluster')

    def test_raises_on_multiple_running_slugs(self):
        self.fargate.seed_cluster_with_tags('my-cluster', _OUR_STACK_TAG)
        self.fargate.seed_task_with_tags('my-cluster', {'VaultApp__Slug': 'slug-a'})
        self.fargate.seed_task_with_tags('my-cluster', {'VaultApp__Slug': 'slug-b'})
        with self.assertRaises(ValueError) as ctx:
            self.resolver.resolve('my-cluster')
        assert 'Ambiguous' in str(ctx.exception)

    def test_ambiguity_error_lists_candidate_slugs(self):
        self.fargate.seed_cluster_with_tags('my-cluster', _OUR_STACK_TAG)
        self.fargate.seed_task_with_tags('my-cluster', {'VaultApp__Slug': 'slug-a'})
        self.fargate.seed_task_with_tags('my-cluster', {'VaultApp__Slug': 'slug-b'})
        with self.assertRaises(ValueError) as ctx:
            self.resolver.resolve('my-cluster')
        msg = str(ctx.exception)
        assert 'slug-a' in msg and 'slug-b' in msg

    def test_tasks_without_slug_tag_ignored(self):
        self.fargate.seed_cluster_with_tags('my-cluster', _OUR_STACK_TAG)
        self.fargate.seed_task_with_tags('my-cluster', {})                     # no VaultApp__Slug tag
        self.fargate.seed_task_with_tags('my-cluster', {'VaultApp__Slug': 'only-slug'})
        result = self.resolver.resolve('my-cluster')
        assert result == 'only-slug'

    # ── check_unique ─────────────────────────────────────────────────────────

    def test_check_unique_passes_when_no_collision(self):
        self.fargate.seed_cluster_with_tags('my-cluster', _OUR_STACK_TAG)
        self.fargate.seed_task_with_tags('my-cluster', {'VaultApp__Slug': 'other-slug'})
        self.resolver.check_unique('my-cluster', 'new-slug')                   # must not raise

    def test_check_unique_raises_on_collision(self):
        self.fargate.seed_cluster_with_tags('my-cluster', _OUR_STACK_TAG)
        self.fargate.seed_task_with_tags('my-cluster', {'VaultApp__Slug': 'dinis-tue'})
        with self.assertRaises(ValueError) as ctx:
            self.resolver.check_unique('my-cluster', 'dinis-tue')
        assert 'dinis-tue' in str(ctx.exception)
        assert 'my-cluster' in str(ctx.exception)

    def test_check_unique_passes_empty_cluster(self):
        self.fargate.seed_cluster_with_tags('my-cluster', _OUR_STACK_TAG)
        self.resolver.check_unique('my-cluster', 'new-slug')                   # empty cluster, must not raise
