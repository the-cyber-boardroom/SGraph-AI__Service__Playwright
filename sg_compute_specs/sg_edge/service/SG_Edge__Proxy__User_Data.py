# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge: SG_Edge__Proxy__User_Data
# Builds the EC2 user-data (cloud-init bash) that brings up a Phase 1 edge proxy:
# write the bundled OpenResty config to disk, read the instance id from IMDS, and
# run the OpenResty container on :80 with the config mounted. The proxy never
# touches AWS APIs (brief 02 — minimal IAM); EDGE_INSTANCE_ID is read from the
# metadata service, not an SDK call. The exact same nginx.conf is reused by the
# local docker-compose stack, so dev and prod behave identically.
# ═══════════════════════════════════════════════════════════════════════════════

import os

from osbot_utils.type_safe.Type_Safe import Type_Safe

PROXY_IMAGE      = 'openresty/openresty:alpine'                                       # the proxy container image
NGINX_CONF_PATH  = os.path.join(os.path.dirname(__file__), '..', 'proxy', 'nginx.conf')
CONTAINER_CONF   = '/usr/local/openresty/nginx/conf/nginx.conf'                       # where the openresty image reads its config
HEREDOC_MARKER   = 'SG_EDGE_NGINX_EOF'


class SG_Edge__Proxy__User_Data(Type_Safe):
    version : str = 'dev'
    image   : str = PROXY_IMAGE

    def nginx_conf(self) -> str:                                                     # the bundled OpenResty config (shared with docker-compose)
        with open(os.path.abspath(NGINX_CONF_PATH)) as f:
            return f.read()

    def render(self) -> str:                                                         # the cloud-init bash user-data
        return (
            '#!/bin/bash\n'
            'set -euo pipefail\n'
            'mkdir -p /etc/sg-edge\n'
            f"cat > /etc/sg-edge/nginx.conf <<'{HEREDOC_MARKER}'\n"
            f'{self.nginx_conf()}\n'
            f'{HEREDOC_MARKER}\n'
            # instance id via IMDSv2 (token flow), fallback to "unknown"
            'TOKEN=$(curl -sX PUT "http://169.254.169.254/latest/api/token" '
            '-H "X-aws-ec2-metadata-token-ttl-seconds: 300" || true)\n'
            'EDGE_INSTANCE_ID=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" '
            'http://169.254.169.254/latest/meta-data/instance-id || echo unknown)\n'
            'docker run -d --name sg-edge --restart always -p 80:80 \\\n'
            '  -e EDGE_INSTANCE_ID="$EDGE_INSTANCE_ID" \\\n'
            f'  -e EDGE_VERSION="{self.version}" \\\n'
            f'  -v /etc/sg-edge/nginx.conf:{CONTAINER_CONF}:ro \\\n'
            f'  {self.image}\n'
        )
