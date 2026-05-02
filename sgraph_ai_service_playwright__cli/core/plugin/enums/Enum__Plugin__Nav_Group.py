# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__Plugin__Nav_Group
# Top-level grouping for the dashboard navigation sidebar.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Plugin__Nav_Group(str, Enum):
    COMPUTE       = 'compute'        # EC2-backed workloads: docker, podman, firefox, neko, vnc
    OBSERVABILITY = 'observability'  # metrics + search: prometheus, elastic, opensearch
    STORAGE       = 'storage'        # future: S3, EFS, vault-backed
