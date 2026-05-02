# ═══════════════════════════════════════════════════════════════════════════════
# Ephemeral EC2 — Section__Node
# Installs Node.js via NodeSource binary distribution and pnpm globally.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

TEMPLATE = """
# ── Node.js {node_major} + pnpm ──────────────────────────────────────────────
echo "[ephemeral-ec2] installing Node.js {node_major}..."
curl -fsSL https://rpm.nodesource.com/setup_{node_major}.x | bash -
dnf install -y nodejs
node --version
npm install -g pnpm
pnpm --version
echo "[ephemeral-ec2] Node.js + pnpm ready"
"""


class Section__Node(Type_Safe):
    node_major : int = 24

    def render(self, node_major: int = 0) -> str:
        major = node_major or self.node_major
        return TEMPLATE.format(node_major=major)
