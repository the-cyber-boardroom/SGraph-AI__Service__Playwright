# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Section__Agent_Tools
# Installs Python venv with the libraries used by the agent_tools sidecar
# surface (httpx, requests, rich). Sets up a logrotate drop-in.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

TEMPLATE = '''\
# ── Agent-tools venv (Python 3.13) ────────────────────────────────────────────
echo '[sg-compute] preparing agent-tools venv...'
dnf install -y git python3.13 jq curl wget
sudo -u ec2-user python3.13 -m venv /home/ec2-user/venvs/agent-tools
sudo -u ec2-user /home/ec2-user/venvs/agent-tools/bin/pip install --upgrade pip requests httpx rich
mkdir -p /var/log/sg-compute
cat > /etc/logrotate.d/sg-compute << 'EOF'
/var/log/sg-compute/*.log {
  daily
  rotate 7
  compress
  missingok
  notifempty
  copytruncate
}
EOF
'''


class Section__Agent_Tools(Type_Safe):

    def render(self) -> str:
        return TEMPLATE
