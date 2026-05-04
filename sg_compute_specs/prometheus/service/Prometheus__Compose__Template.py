# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Prometheus: Prometheus__Compose__Template
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe


PROM_IMAGE          = 'prom/prometheus:latest'
CADVISOR_IMAGE      = 'gcr.io/cadvisor/cadvisor:latest'
NODE_EXPORTER_IMAGE = 'prom/node-exporter:latest'
PROMETHEUS_RETENTION = '24h'


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


PLACEHOLDERS = ('prom_image', 'cadvisor_image', 'node_exporter_image', 'retention')  # Locked by test


class Prometheus__Compose__Template(Type_Safe):

    def render(self, retention          : str = PROMETHEUS_RETENTION,
                     prom_image         : str = PROM_IMAGE          ,
                     cadvisor_image     : str = CADVISOR_IMAGE      ,
                     node_exporter_image: str = NODE_EXPORTER_IMAGE ) -> str:
        return COMPOSE_TEMPLATE.format(prom_image          = str(prom_image)         ,
                                       cadvisor_image      = str(cadvisor_image)     ,
                                       node_exporter_image = str(node_exporter_image),
                                       retention           = str(retention)          )
