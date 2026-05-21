# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute_specs vault_app/fargate — Vault_App__Fargate__Tags__Reader
# Reads VaultApp__* tags from an ECS cluster → Schema__VAF__Cluster__Config.
# Depends on Fargate__AWS__Client.describe_cluster(); returns a safe empty
# config on missing cluster or missing tags.
# ═══════════════════════════════════════════════════════════════════════════════

from typing import Any

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute_specs.vault_app.fargate.schemas.Schema__VAF__Cluster__Config import Schema__VAF__Cluster__Config


class Vault_App__Fargate__Tags__Reader(Type_Safe):
    fargate_client : Any    = None                                              # Fargate__AWS__Client injected by caller

    def read(self, cluster_name: str) -> Schema__VAF__Cluster__Config:         # describe cluster → extract tags
        if not self.fargate_client:
            return Schema__VAF__Cluster__Config(cluster_name=cluster_name)
        cluster = self.fargate_client.describe_cluster(cluster_name)
        if cluster is None:
            return Schema__VAF__Cluster__Config(cluster_name=cluster_name)
        tags = cluster.tags or {}
        subnets_raw = tags.get('VaultApp__Subnets', '')                          # space-separated in tag (AWS commas disallowed)
        subnets_csv = ','.join(s for s in subnets_raw.replace(',', ' ').split() if s)
        return Schema__VAF__Cluster__Config(
            cluster_name       = cluster_name,
            subnets            = subnets_csv,                                    # canonical CSV for downstream consumers
            security_group     = tags.get('VaultApp__SecurityGroup',    ''),
            dns_zone           = tags.get('VaultApp__DnsZone',          ''),
            execution_role_arn = tags.get('VaultApp__ExecutionRoleArn', ''),
            task_role_arn      = tags.get('VaultApp__TaskRoleArn',      ''),
            log_group          = tags.get('VaultApp__LogGroup',         ''),
            ecr_repo_name      = tags.get('VaultApp__EcrRepoName',      ''),
            region             = tags.get('VaultApp__Region',           ''),
            created_at         = tags.get('VaultApp__CreatedAt',        ''),
        )
