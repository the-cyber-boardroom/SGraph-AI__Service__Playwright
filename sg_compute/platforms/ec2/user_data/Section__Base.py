# ═══════════════════════════════════════════════════════════════════════════════
# Ephemeral EC2 — Section__Base
# Bash preamble: strict mode, logging, hostname, essential packages.
# Every stack user-data script starts with this section.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

LOG_FILE = '/var/log/ephemeral-ec2-boot.log'

TEMPLATE = '''\
#!/usr/bin/env bash
set -euo pipefail
mkdir -p /var/lib
trap 'rc=$?; echo "[ephemeral-ec2] boot FAILED at line $LINENO (exit=$rc)"; touch /var/lib/sg-compute-boot-failed' ERR
exec > >(tee -a {log_file}) 2>&1
echo "[ephemeral-ec2] boot starting: {stack_name} at $(date -u +%FT%TZ)"

hostnamectl set-hostname {stack_name} 2>/dev/null || true
dnf update -y -q
dnf install -y --allowerasing git curl jq unzip

# SSM agent ships on AL2023 — ensure it is running
systemctl enable --now amazon-ssm-agent 2>/dev/null || true
'''


class Section__Base(Type_Safe):

    def render(self, stack_name: str) -> str:
        return TEMPLATE.format(stack_name=stack_name, log_file=LOG_FILE)
