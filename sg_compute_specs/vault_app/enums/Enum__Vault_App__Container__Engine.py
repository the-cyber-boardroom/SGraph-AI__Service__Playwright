# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-app: Enum__Vault_App__Container__Engine
# Which container engine the EC2 host uses to run the stack. DOCKER is the
# default; PODMAN is offered so boot-time / runtime experiments can compare the
# two on identical compose files.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Vault_App__Container__Engine(Enum):
    DOCKER = 'docker'   # Docker CE + compose plugin
    PODMAN = 'podman'   # Podman + podman-compose (daemonless)
