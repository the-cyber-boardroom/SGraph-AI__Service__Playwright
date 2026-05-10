# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Section__SGit_Venv
# Installs sgit in a Python 3.12 venv under ~/claude-session-venv for ssm-user.
# sgit provides encrypted vault storage that turns ephemeral instances into
# durable workflows: work in vault → vault syncs to remote → replacement instance
# pulls vault → continues. The venv is usable immediately via activating or
# calling the binary at ~/claude-session-venv/bin/sgit directly.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

TEMPLATE = '''\
# ── sgit venv (python3.12) ────────────────────────────────────────────────────
echo '[sg-compute] installing sgit venv...'
sudo -u ssm-user python3.12 -m venv /home/ssm-user/claude-session-venv
sudo -u ssm-user /home/ssm-user/claude-session-venv/bin/pip install --quiet --upgrade pip sgit
echo "[sg-compute] sgit ready"
'''


class Section__SGit_Venv(Type_Safe):

    def render(self) -> str:
        return TEMPLATE
