# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute_specs vault_app/fargate — Vault_App__Fargate__Tags__Writer
# Builds the VaultApp__* ECS cluster tag dict written during setup create.
# No AWS calls — pure dict construction.  Tags__Reader is the symmetric reader.
# ═══════════════════════════════════════════════════════════════════════════════

from datetime import datetime, timezone

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Vault_App__Fargate__Tags__Writer(Type_Safe):

    def tags_for_cluster(self, cluster_name: str, subnets: str,
                          security_group: str, execution_role_arn: str,
                          log_group: str, ecr_repo_name: str, region: str,
                          task_role_arn: str = '', dns_zone: str = '') -> dict:  # full tag dict for Fargate client
        tags = {
            'Stack'                     : 'sg-vault-app-fargate',
            'VaultApp__Subnets'         : subnets,
            'VaultApp__SecurityGroup'   : security_group,
            'VaultApp__ExecutionRoleArn': execution_role_arn,
            'VaultApp__LogGroup'        : log_group,
            'VaultApp__EcrRepoName'     : ecr_repo_name,
            'VaultApp__Region'          : region,
            'VaultApp__CreatedAt'       : datetime.now(timezone.utc).isoformat(),
        }
        if task_role_arn:                                                        # optional — only present if non-empty
            tags['VaultApp__TaskRoleArn'] = task_role_arn
        if dns_zone:                                                             # optional — only present if non-empty
            tags['VaultApp__DnsZone'] = dns_zone
        return tags
