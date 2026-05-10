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
usermod -aG docker ssm-user  || true
docker --version
echo "[ephemeral-ec2] Docker ready"
'''


class Section__Docker(Type_Safe):

    def render(self) -> str:
        return TEMPLATE
