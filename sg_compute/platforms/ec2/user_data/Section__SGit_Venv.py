# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Section__SGit_Venv
# Installs sgit in a Python 3.13 venv under ~/claude-session-venv for ssm-user.
# sgit requires Python ≥ 3.13. AL2023 ships python3.12 by default; we install
# python3.13 explicitly from the standard AL2023 repos.
# sgit provides encrypted vault storage that turns ephemeral instances into
# durable workflows: work in vault → vault syncs to remote → replacement instance
# pulls vault → continues. The venv is usable immediately via activating or
# calling the binary at ~/claude-session-venv/bin/sgit directly.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

TEMPLATE = '''\
# ── sgit venv (python3.13) ────────────────────────────────────────────────────
echo '[sg-compute] waiting for ssm-user...'
until id ssm-user >/dev/null 2>&1; do sleep 2; done
echo '[sg-compute] installing python3.13 and sgit venv...'
dnf install -y python3.13 python3.13-pip
sudo -u ssm-user python3.13 -m venv /home/ssm-user/claude-session-venv
sudo -u ssm-user /home/ssm-user/claude-session-venv/bin/pip install --quiet --upgrade pip sgit
echo "[sg-compute] sgit ready"
'''


class Section__SGit_Venv(Type_Safe):

    def render(self) -> str:
        return TEMPLATE
