# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__Stack__Component__Kind
# Identifies which AWS service a stack-component schema represents.
# Used by renderers to pick the right label/icon without inspecting the class.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Stack__Component__Kind(str, Enum):
    AMP        = 'amp'                                                              # Amazon Managed Prometheus workspace
    OPENSEARCH = 'opensearch'                                                       # Amazon OpenSearch domain
    GRAFANA    = 'grafana'                                                          # Amazon Managed Grafana workspace

    def __str__(self):
        return self.value
