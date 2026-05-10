# ═══════════════════════════════════════════════════════════════════════════════
# Ephemeral EC2 — Section__Docker
# Installs Docker CE on AL2023 and enables the socket.
# Used as baseline container engine even when the app itself runs bare.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

TEMPLATE = '''
# ── Docker CE ─────────────────────────────────────────────────────────────────
echo "[ephemeral-ec2] installing Docker CE..."
dnf install -y docker
systemctl enable --now docker
usermod -aG docker ec2-user  || true
# ssm-user is created by SSM agent on first Session Manager session, not at boot.
# Background the wait so the main boot script is never blocked.
(
    count=0
    while [ $count -lt 150 ]; do
        if id ssm-user >/dev/null 2>&1; then
            usermod -aG docker ssm-user
            echo "[ephemeral-ec2] ssm-user added to docker group"
            break
        fi
        sleep 2
        count=$((count + 1))
    done
) &
docker --version
echo "[ephemeral-ec2] Docker ready"
'''


class Section__Docker(Type_Safe):

    def render(self) -> str:
        return TEMPLATE
