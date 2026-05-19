# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute_specs vault_app/fargate — Vault_App__Fargate__Spec
# Pure constants for the vault container — image, ports, env contract.
# No AWS calls.  Single source of truth for start / setup orchestrators.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Vault_App__Fargate__Spec(Type_Safe):
    image_repo_name        : str = 'sg-send-vault'
    image_tag              : str = 'latest'
    container_name         : str = 'vault'
    health_path            : str = '/info/health'
    http_port              : int = 8080
    https_port             : int = 443
    acme_port              : int = 80
    default_cpu            : str = '512'
    default_memory         : str = '1024'
    default_log_group      : str = '/ecs/vault-app'
    default_cluster        : str = 'vault-app'
    default_task_def_family: str = 'vault-app'

    def env_for_run(self, access_token: str,
                    seed_vault_keys: str = '', with_tls: bool = True) -> dict:  # env-var dict the vault container expects
        # SEND__STORAGE_MODE is ALWAYS 'memory' — Q1/Q6 decision, no flag
        env = {
            'SEND__STORAGE_MODE': 'memory',
            'SEND__ACCESS_TOKEN': access_token,
        }
        if seed_vault_keys:
            env['SEND__SEED_VAULT_KEYS'] = seed_vault_keys
        if with_tls:
            env['SEND__TLS_ENABLED'] = 'true'
        return env

    def port_mappings(self) -> list:                                            # list of dicts for task-def register
        return [
            {'containerPort': self.http_port,  'protocol': 'tcp'},
            {'containerPort': self.https_port, 'protocol': 'tcp'},
            {'containerPort': self.acme_port,  'protocol': 'tcp'},
        ]
