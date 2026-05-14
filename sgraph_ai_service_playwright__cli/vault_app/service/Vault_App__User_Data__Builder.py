# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Vault_App__User_Data__Builder
# Builds the EC2 user-data shell script that:
#   1. Installs docker + docker-compose (AL2023 base)
#   2. Writes the rendered docker-compose.yml
#   3. Pulls all images and starts the stack
# Pure templating; no AWS calls.
# ═══════════════════════════════════════════════════════════════════════════════

import base64

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

COMPOSE_DIR = '/opt/vault-app'

USER_DATA_TEMPLATE = """\
#!/bin/bash
set -euo pipefail

# Install docker and docker-compose-plugin (AL2023)
dnf install -y docker
systemctl enable --now docker
dnf install -y docker-compose-plugin

mkdir -p {compose_dir}
cat > {compose_dir}/docker-compose.yml << 'COMPOSE_EOF'
{compose_yaml}
COMPOSE_EOF

mkdir -p {compose_dir}/data

cd {compose_dir}
docker compose pull
docker compose up -d

# Tag this instance with the stack name for discovery
instance_id=$(ec2-metadata --instance-id | cut -d' ' -f2)
region=$(ec2-metadata --availability-zone | cut -d' ' -f2 | head -c -2)
aws ec2 create-tags --region "$region" \
  --resources "$instance_id" \
  --tags Key=sg:stack-name,Value={stack_name}
"""


class Vault_App__User_Data__Builder(Type_Safe):

    def build(self, compose_yaml: str, stack_name: str) -> str:                     # returns base64-encoded user-data for EC2
        script = USER_DATA_TEMPLATE.format(
            compose_dir  = COMPOSE_DIR   ,
            compose_yaml = compose_yaml  ,
            stack_name   = stack_name    ,
        )
        return base64.b64encode(script.encode()).decode()
