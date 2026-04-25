# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Elastic__User__Data__Builder
# Renders the cloud-init bash script that boots a single AL2023 EC2 instance
# into a working Elasticsearch + Kibana + nginx-TLS stack.
#
# Topology on the instance
# ────────────────────────
#   /opt/sg-elastic/
#     docker-compose.yml   — elasticsearch:8.13.4, kibana:8.13.4, nginx:alpine
#     nginx.conf           — TLS termination on :443, path-based routing
#     certs/{tls.crt, tls.key}  — self-signed cert generated at boot
#     .env                 — ELASTIC_PASSWORD=... (chmod 600)
#
# Port surface
#   :443 (public)  → nginx TLS
#                      /            → kibana:5601
#                      /_elastic/*  → elasticsearch:9200 (prefix stripped)
#   :9200/:5601    → 127.0.0.1-bound only; not reachable from the SG
#
# The ELASTIC_PASSWORD is provided by the caller (pinned client-side before
# launch) so `sp elastic create` can return it in the response without any
# post-boot retrieval round trip. It is written to /opt/sg-elastic/.env with
# 0600 perms; never echoed to the boot log.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text
from osbot_utils.type_safe.type_safe_core.decorators.type_safe                      import type_safe

from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Elastic__Password    import Safe_Str__Elastic__Password
from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Elastic__Stack__Name import Safe_Str__Elastic__Stack__Name


ELASTIC_VERSION = '8.13.4'                                                          # Matches library/docs/ops/v0.1.72__elastic-kibana-ec2.md spec
KIBANA_VERSION  = '8.13.4'
NGINX_VERSION   = 'alpine'
ES_JAVA_OPTS    = '-Xms4g -Xmx4g'                                                   # Default sized for m6i.xlarge (16 GB). Kibana ~1.5 GB + nginx + OS = comfortable on 16 GB. Override via Elastic__User__Data__Builder(es_java_opts=...) for smaller boxes.


USER_DATA_TEMPLATE = """\
#!/bin/bash
set -euxo pipefail
exec > >(tee /var/log/sg-elastic-start.log | logger -t sg-elastic) 2>&1

BOOT_STATUS_FILE=/var/log/sg-elastic-boot-status
echo "PENDING $(date --iso-8601=seconds)" > "$BOOT_STATUS_FILE"
trap 'echo "FAILED at $(date --iso-8601=seconds) — exit $?" > "$BOOT_STATUS_FILE"' EXIT

echo "=== SG Elastic boot at $(date) — stack={stack_name} ==="

# ── Docker + Compose plugin ────────────────────────────────────────────────────
dnf update -y
dnf install -y docker openssl
systemctl enable --now docker
usermod -aG docker ec2-user
mkdir -p /usr/local/lib/docker/cli-plugins
curl -fsSL https://github.com/docker/compose/releases/download/v2.27.0/docker-compose-linux-x86_64 \
    -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# ── Kernel + ulimit tweaks Elasticsearch wants ─────────────────────────────────
sysctl -w vm.max_map_count=262144
echo 'vm.max_map_count=262144' > /etc/sysctl.d/99-elastic.conf

# ── Stack directory + password env ─────────────────────────────────────────────
mkdir -p /opt/sg-elastic/certs
umask 077
KIBANA_ENCRYPTION_KEY=$(openssl rand -hex 32)                                  # 64 hex chars — meets Kibana's >= 32-byte requirement for xpack.encryptedSavedObjects (8.10+ exits 78 without it)
cat > /opt/sg-elastic/.env <<'EOF_ENV'
ELASTIC_PASSWORD={elastic_password}
EOF_ENV
echo "KIBANA_ENCRYPTION_KEY=${{KIBANA_ENCRYPTION_KEY}}" >> /opt/sg-elastic/.env
chmod 600 /opt/sg-elastic/.env
umask 022

# ── Self-signed TLS cert (SAN = public IP; fine for ephemeral) ─────────────────
openssl req -x509 -newkey rsa:2048 -nodes -days 30 \
    -keyout /opt/sg-elastic/certs/tls.key \
    -out    /opt/sg-elastic/certs/tls.crt \
    -subj "/CN=sg-elastic-{stack_name}"
chmod 600 /opt/sg-elastic/certs/tls.key
chmod 644 /opt/sg-elastic/certs/tls.crt

# ── nginx.conf ─────────────────────────────────────────────────────────────────
cat > /opt/sg-elastic/nginx.conf <<'EOF_NGINX'
events {{}}
http {{
  client_max_body_size 100m;

  upstream kibana        {{ server kibana:5601; }}
  upstream elasticsearch {{ server elasticsearch:9200; }}

  server {{
    listen 443 ssl;
    server_name _;

    ssl_certificate     /etc/nginx/certs/tls.crt;
    ssl_certificate_key /etc/nginx/certs/tls.key;

    location /_elastic/ {{
      rewrite ^/_elastic/(.*)$ /$1 break;
      proxy_pass http://elasticsearch;
      proxy_set_header Host              $host;
      proxy_set_header X-Real-IP         $remote_addr;
      proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
      proxy_set_header Authorization     $http_authorization;
      proxy_pass_request_headers on;
    }}

    location / {{
      proxy_pass http://kibana;
      proxy_http_version 1.1;
      proxy_set_header Host              $host;
      proxy_set_header X-Real-IP         $remote_addr;
      proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
      proxy_set_header Upgrade           $http_upgrade;
      proxy_set_header Connection        "upgrade";
    }}
  }}
}}
EOF_NGINX

# ── docker-compose.yml ─────────────────────────────────────────────────────────
cat > /opt/sg-elastic/docker-compose.yml <<'EOF_COMPOSE'
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:{elastic_version}
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=true
      - xpack.security.http.ssl.enabled=false
      - xpack.security.transport.ssl.enabled=false
      - ELASTIC_PASSWORD=${{ELASTIC_PASSWORD}}
      - ES_JAVA_OPTS={es_java_opts}
    ulimits:
      memlock: {{ soft: -1, hard: -1 }}
    ports:
      - "127.0.0.1:9200:9200"
    restart: unless-stopped

  kibana:
    image: docker.elastic.co/kibana/kibana:{kibana_version}
    environment:
      # Service-account token auth — Kibana 8.x refuses ELASTICSEARCH_USERNAME=elastic (the superuser).
      # The token is minted by user-data after ES is up, then injected via --env-file.
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
      - ELASTICSEARCH_SERVICEACCOUNTTOKEN=${{KIBANA_SERVICE_TOKEN}}
      - XPACK_ENCRYPTEDSAVEDOBJECTS_ENCRYPTIONKEY=${{KIBANA_ENCRYPTION_KEY}}
      - XPACK_SECURITY_ENCRYPTIONKEY=${{KIBANA_ENCRYPTION_KEY}}
      - XPACK_REPORTING_ENCRYPTIONKEY=${{KIBANA_ENCRYPTION_KEY}}
      - SERVER_PUBLICBASEURL=https://localhost
    depends_on:
      - elasticsearch
    ports:
      - "127.0.0.1:5601:5601"
    restart: unless-stopped

  nginx:
    image: nginx:{nginx_version}
    ports:
      - "443:443"
    volumes:
      - /opt/sg-elastic/nginx.conf:/etc/nginx/nginx.conf:ro
      - /opt/sg-elastic/certs:/etc/nginx/certs:ro
    depends_on:
      - kibana
    restart: unless-stopped
EOF_COMPOSE

# ── Launch stack (staged: ES → token mint → Kibana + nginx) ───────────────────
cd /opt/sg-elastic

# 1) Start Elasticsearch first. Kibana 8.x refuses ELASTICSEARCH_USERNAME=elastic
#    (the superuser) so we mint a service-account token after ES is healthy and
#    hand that to Kibana as ELASTICSEARCH_SERVICEACCOUNTTOKEN.
docker compose --env-file /opt/sg-elastic/.env up -d elasticsearch

# 2) Wait for Elasticsearch to accept authenticated requests (up to ~120s).
echo "[$(date --iso-8601=seconds)] Waiting for Elasticsearch /_cluster/health ..."
ES_READY=false
for i in $(seq 1 60); do
    if docker exec sg-elastic-elasticsearch-1 curl -sf \
            -u "elastic:{elastic_password}" http://localhost:9200/_cluster/health >/dev/null 2>&1; then
        echo "[$(date --iso-8601=seconds)] Elasticsearch is ready (attempt $i)"
        ES_READY=true
        break
    fi
    sleep 2
done
[ "$ES_READY" != "true" ] && echo "[$(date --iso-8601=seconds)] WARN: ES never went ready; continuing anyway"

# 3) Mint a service-account token for Kibana. Format is stable:
#    "SERVICE_TOKEN elastic/kibana/<name> = <token>" — we grab the last field.
#    Token name includes a timestamp so retries are idempotent.
TOKEN_NAME="sg-kibana-$(date +%s)"
TOKEN_OUTPUT=$(docker exec sg-elastic-elasticsearch-1 \
                   bin/elasticsearch-service-tokens create elastic/kibana "$TOKEN_NAME")
KIBANA_SERVICE_TOKEN=$(echo "$TOKEN_OUTPUT" | awk -F '= ' '/= /{{print $2; exit}}')
if [ -z "$KIBANA_SERVICE_TOKEN" ]; then
    echo "[$(date --iso-8601=seconds)] FATAL: service-account token mint returned empty; raw: $TOKEN_OUTPUT"
    exit 1
fi

umask 077
echo "KIBANA_SERVICE_TOKEN=${{KIBANA_SERVICE_TOKEN}}" >> /opt/sg-elastic/.env
chmod 600 /opt/sg-elastic/.env
umask 022

# 4) Start Kibana + nginx now that the token is in .env
docker compose --env-file /opt/sg-elastic/.env up -d kibana nginx

echo "=== SG Elastic start complete at $(date) ==="
echo "OK $(date --iso-8601=seconds)" > "$BOOT_STATUS_FILE"
trap - EXIT
"""


class Elastic__User__Data__Builder(Type_Safe):
    elastic_version : Safe_Str__Text = ELASTIC_VERSION
    kibana_version  : Safe_Str__Text = KIBANA_VERSION
    nginx_version   : Safe_Str__Text = NGINX_VERSION
    es_java_opts    : Safe_Str__Text = ES_JAVA_OPTS

    @type_safe
    def render(self, stack_name       : Safe_Str__Elastic__Stack__Name ,
                     elastic_password : Safe_Str__Elastic__Password
                ) -> str:
        return USER_DATA_TEMPLATE.format(stack_name       = str(stack_name      )  ,
                                         elastic_password = str(elastic_password)  ,
                                         elastic_version  = str(self.elastic_version),
                                         kibana_version   = str(self.kibana_version ),
                                         nginx_version    = str(self.nginx_version  ),
                                         es_java_opts     = str(self.es_java_opts   ))
