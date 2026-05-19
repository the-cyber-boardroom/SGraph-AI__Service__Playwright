# ═══════════════════════════════════════════════════════════════════════════════
# tests/unit — test_Vault_App__Fargate__Tags
# Covers: Tags__Writer (tag dict construction) and Tags__Reader (cluster tags →
# Schema__VAF__Cluster__Config), using Fargate__AWS__Client__In_Memory.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sg_compute_specs.vault_app.fargate.service.Vault_App__Fargate__Tags__Writer import Vault_App__Fargate__Tags__Writer
from sg_compute_specs.vault_app.fargate.service.Vault_App__Fargate__Tags__Reader import Vault_App__Fargate__Tags__Reader
from sg_compute_specs.vault_app.fargate.schemas.Schema__VAF__Cluster__Config    import Schema__VAF__Cluster__Config
from tests.unit.sgraph_ai_service_playwright__cli.aws.fargate.service.Fargate__AWS__Client__In_Memory import (
    Fargate__AWS__Client__In_Memory,
)


class test_Vault_App__Fargate__Tags__Writer(TestCase):

    def setUp(self):
        self.writer = Vault_App__Fargate__Tags__Writer()

    def _base_tags(self):
        return self.writer.tags_for_cluster(
            cluster_name      = 'acme-prod',
            subnets           = 'subnet-aaa,subnet-bbb',
            security_group    = 'sg-ccc',
            execution_role_arn= 'arn:aws:iam::123:role/exec-role',
            log_group         = '/ecs/vault-app',
            ecr_repo_name     = 'sg-send-vault',
            region            = 'eu-west-2',
        )

    # ── required keys ────────────────────────────────────────────────────────

    def test_stack_tag_value(self):
        tags = self._base_tags()
        assert tags['Stack'] == 'sg-vault-app-fargate'

    def test_subnets_tag_present(self):
        tags = self._base_tags()
        assert tags['VaultApp__Subnets'] == 'subnet-aaa subnet-bbb'              # CSV → space-separated (AWS tag values disallow commas)

    def test_security_group_tag_present(self):
        tags = self._base_tags()
        assert tags['VaultApp__SecurityGroup'] == 'sg-ccc'

    def test_execution_role_tag_present(self):
        tags = self._base_tags()
        assert tags['VaultApp__ExecutionRoleArn'] == 'arn:aws:iam::123:role/exec-role'

    def test_log_group_tag_present(self):
        tags = self._base_tags()
        assert tags['VaultApp__LogGroup'] == '/ecs/vault-app'

    def test_ecr_repo_name_tag_present(self):
        tags = self._base_tags()
        assert tags['VaultApp__EcrRepoName'] == 'sg-send-vault'

    def test_region_tag_present(self):
        tags = self._base_tags()
        assert tags['VaultApp__Region'] == 'eu-west-2'

    def test_created_at_tag_present_and_iso(self):
        tags = self._base_tags()
        created_at = tags.get('VaultApp__CreatedAt', '')
        assert 'T' in created_at                                                # ISO-8601 has T separator

    # ── optional fields omitted when empty ──────────────────────────────────

    def test_task_role_absent_when_not_given(self):
        tags = self._base_tags()
        assert 'VaultApp__TaskRoleArn' not in tags

    def test_dns_zone_absent_when_not_given(self):
        tags = self._base_tags()
        assert 'VaultApp__DnsZone' not in tags

    def test_task_role_present_when_given(self):
        tags = self.writer.tags_for_cluster(
            cluster_name      = 'x',
            subnets           = 's',
            security_group    = 'sg',
            execution_role_arn= 'exec-arn',
            log_group         = '/ecs/x',
            ecr_repo_name     = 'repo',
            region            = 'us-east-1',
            task_role_arn     = 'arn:aws:iam::123:role/task-role',
        )
        assert tags['VaultApp__TaskRoleArn'] == 'arn:aws:iam::123:role/task-role'

    def test_dns_zone_present_when_given(self):
        tags = self.writer.tags_for_cluster(
            cluster_name      = 'x',
            subnets           = 's',
            security_group    = 'sg',
            execution_role_arn= 'exec-arn',
            log_group         = '/ecs/x',
            ecr_repo_name     = 'repo',
            region            = 'us-east-1',
            dns_zone          = 'sg-compute.sgraph.ai',
        )
        assert tags['VaultApp__DnsZone'] == 'sg-compute.sgraph.ai'

    def test_returns_dict(self):
        assert isinstance(self._base_tags(), dict)


class test_Vault_App__Fargate__Tags__Reader(TestCase):

    def setUp(self):
        self.fargate = Fargate__AWS__Client__In_Memory()
        self.writer  = Vault_App__Fargate__Tags__Writer()
        self.reader  = Vault_App__Fargate__Tags__Reader(fargate_client=self.fargate)

    def _seed(self, cluster_name: str, **kwargs):
        tags = self.writer.tags_for_cluster(
            cluster_name      = cluster_name,
            subnets           = kwargs.get('subnets',            'subnet-x'),
            security_group    = kwargs.get('security_group',     'sg-x'),
            execution_role_arn= kwargs.get('execution_role_arn', 'arn:exec'),
            log_group         = kwargs.get('log_group',          '/ecs/test'),
            ecr_repo_name     = kwargs.get('ecr_repo_name',      'sg-send-vault'),
            region            = kwargs.get('region',             'eu-west-2'),
            task_role_arn     = kwargs.get('task_role_arn',      ''),
            dns_zone          = kwargs.get('dns_zone',           ''),
        )
        self.fargate.seed_cluster_with_tags(cluster_name, tags)

    # ── happy path ───────────────────────────────────────────────────────────

    def test_read_returns_schema_type(self):
        self._seed('acme-prod')
        cfg = self.reader.read('acme-prod')
        assert isinstance(cfg, Schema__VAF__Cluster__Config)

    def test_read_cluster_name_set(self):
        self._seed('acme-prod')
        cfg = self.reader.read('acme-prod')
        assert cfg.cluster_name == 'acme-prod'

    def test_read_subnets_extracted(self):
        self._seed('acme-prod', subnets='subnet-aaa,subnet-bbb')
        cfg = self.reader.read('acme-prod')
        assert cfg.subnets == 'subnet-aaa,subnet-bbb'

    def test_read_security_group_extracted(self):
        self._seed('acme-prod', security_group='sg-ccc')
        cfg = self.reader.read('acme-prod')
        assert cfg.security_group == 'sg-ccc'

    def test_read_execution_role_arn_extracted(self):
        self._seed('acme-prod', execution_role_arn='arn:aws:iam::123:role/exec')
        cfg = self.reader.read('acme-prod')
        assert cfg.execution_role_arn == 'arn:aws:iam::123:role/exec'

    def test_read_log_group_extracted(self):
        self._seed('acme-prod', log_group='/ecs/vault-app')
        cfg = self.reader.read('acme-prod')
        assert cfg.log_group == '/ecs/vault-app'

    def test_read_ecr_repo_name_extracted(self):
        self._seed('acme-prod', ecr_repo_name='sg-send-vault')
        cfg = self.reader.read('acme-prod')
        assert cfg.ecr_repo_name == 'sg-send-vault'

    def test_read_region_extracted(self):
        self._seed('acme-prod', region='eu-west-2')
        cfg = self.reader.read('acme-prod')
        assert cfg.region == 'eu-west-2'

    def test_read_dns_zone_extracted_when_present(self):
        self._seed('acme-prod', dns_zone='sg-compute.sgraph.ai')
        cfg = self.reader.read('acme-prod')
        assert cfg.dns_zone == 'sg-compute.sgraph.ai'

    def test_read_task_role_arn_extracted_when_present(self):
        self._seed('acme-prod', task_role_arn='arn:aws:iam::123:role/task')
        cfg = self.reader.read('acme-prod')
        assert cfg.task_role_arn == 'arn:aws:iam::123:role/task'

    # ── missing cluster ──────────────────────────────────────────────────────

    def test_read_missing_cluster_returns_empty_config(self):
        cfg = self.reader.read('nonexistent-cluster')
        assert isinstance(cfg, Schema__VAF__Cluster__Config)
        assert cfg.cluster_name == 'nonexistent-cluster'
        assert cfg.subnets == ''
        assert cfg.security_group == ''

    def test_read_no_client_returns_empty_config(self):
        reader = Vault_App__Fargate__Tags__Reader()
        cfg = reader.read('any-cluster')
        assert cfg.cluster_name == 'any-cluster'
        assert cfg.subnets == ''
