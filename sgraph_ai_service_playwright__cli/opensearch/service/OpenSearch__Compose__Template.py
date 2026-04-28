# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — OpenSearch__Compose__Template
# Renders the docker-compose.yml that boots OpenSearch + Dashboards on the
# EC2 host. Single responsibility: string templating with safe substitutions.
# Mirrors the User_Data__Builder shape — placeholder set is locked by test
# so future expansion (TLS certs, plugin install, JVM tuning) lands in
# isolated slices.
#
# Doc 4 OS1 sign-off: images use the moving 'latest' tag in production;
# tests can override the image via the OS_IMAGE / DASHBOARDS_IMAGE constants
# to pin a known version.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe


OS_IMAGE         = 'opensearchproject/opensearch:latest'                            # Per plan doc 4 OS1 — moving tag in production; tests pin
DASHBOARDS_IMAGE = 'opensearchproject/opensearch-dashboards:latest'

# docker-compose.yml template — single-node OpenSearch + Dashboards
COMPOSE_TEMPLATE = """\
services:
  opensearch:
    image: {os_image}
    container_name: sg-opensearch
    environment:
      - cluster.name=sg-opensearch-cluster
      - node.name=sg-opensearch-node
      - discovery.type=single-node
      - bootstrap.memory_lock=true
      - OPENSEARCH_JAVA_OPTS=-Xms{heap_size} -Xmx{heap_size}
      - OPENSEARCH_INITIAL_ADMIN_PASSWORD={admin_password}
    ulimits:
      memlock:
        soft: -1
        hard: -1
      nofile:
        soft: 65536
        hard: 65536
    volumes:
      - opensearch-data:/usr/share/opensearch/data
    networks:
      - sg-net

  dashboards:
    image: {dashboards_image}
    container_name: sg-opensearch-dashboards
    environment:
      - OPENSEARCH_HOSTS=https://opensearch:9200
      - OPENSEARCH_USERNAME=admin
      - OPENSEARCH_PASSWORD={admin_password}
    networks:
      - sg-net
    depends_on:
      - opensearch

networks:
  sg-net:
    driver: bridge

volumes:
  opensearch-data:
"""


PLACEHOLDERS = ('os_image', 'dashboards_image', 'admin_password', 'heap_size')      # Locked by test


class OpenSearch__Compose__Template(Type_Safe):

    def render(self, admin_password: str, heap_size: str = '2g',
                     os_image: str = OS_IMAGE, dashboards_image: str = DASHBOARDS_IMAGE) -> str:
        return COMPOSE_TEMPLATE.format(os_image         = str(os_image)         ,
                                       dashboards_image = str(dashboards_image) ,
                                       admin_password   = str(admin_password)   ,
                                       heap_size        = str(heap_size)        )
