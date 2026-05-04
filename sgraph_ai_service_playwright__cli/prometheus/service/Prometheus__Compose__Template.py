# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Prometheus__Compose__Template
# Renders the docker-compose.yml that boots Prometheus + cAdvisor +
# node-exporter on the EC2 host. Single responsibility: string templating.
# Mirrors OpenSearch__Compose__Template — placeholder set is locked by test.
#
# Per plan doc 5:
#   P1 — no Grafana / no Dashboards container in this stack.
#   P2 — true ephemeral; no EBS; 24h Prometheus retention.
#   P4 — moving 'latest' tags in production; tests pin a known version.
#
# prometheus.yml is rendered upstream by Prometheus__Config__Generator and
# bind-mounted at /opt/sg-prometheus/prometheus.yml.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe


PROM_IMAGE          = 'prom/prometheus:latest'                                      # P4 — moving tag in prod; tests pin
CADVISOR_IMAGE      = 'gcr.io/cadvisor/cadvisor:latest'
NODE_EXPORTER_IMAGE = 'prom/node-exporter:latest'

PROMETHEUS_RETENTION = '24h'                                                        # P2 — Prometheus self-prunes after 24h


# docker-compose.yml template — 3 services on the sg-net bridge
COMPOSE_TEMPLATE = """\
services:
  prometheus:
    image: {prom_image}
    container_name: sg-prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.retention.time={retention}'
    volumes:
      - /opt/sg-prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
    ports:
      - "9090:9090"
    networks:
      - sg-net
    restart: unless-stopped

  cadvisor:
    image: {cadvisor_image}
    container_name: sg-cadvisor
    volumes:
      - /:/rootfs:ro
      - /var/run:/var/run:ro
      - /sys:/sys:ro
      - /var/lib/docker:/var/lib/docker:ro
    networks:
      - sg-net
    restart: unless-stopped

  node-exporter:
    image: {node_exporter_image}
    container_name: sg-node-exporter
    pid: host
    networks:
      - sg-net
    restart: unless-stopped

networks:
  sg-net:
    driver: bridge
"""


PLACEHOLDERS = ('prom_image', 'cadvisor_image', 'node_exporter_image', 'retention') # Locked by test


class Prometheus__Compose__Template(Type_Safe):

    def render(self, retention          : str = PROMETHEUS_RETENTION,
                     prom_image         : str = PROM_IMAGE          ,
                     cadvisor_image     : str = CADVISOR_IMAGE      ,
                     node_exporter_image: str = NODE_EXPORTER_IMAGE ) -> str:
        return COMPOSE_TEMPLATE.format(prom_image          = str(prom_image)         ,
                                       cadvisor_image      = str(cadvisor_image)     ,
                                       node_exporter_image = str(node_exporter_image),
                                       retention           = str(retention)          )
