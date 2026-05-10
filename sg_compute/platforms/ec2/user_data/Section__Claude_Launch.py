# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Section__Claude_Launch
# Bash fragment that boots Claude under tmux when --with-claude is set.
# Returns the empty string when disabled (no-op).
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

TEMPLATE = '''\
# ── Claude launch (tmux) ──────────────────────────────────────────────────────
echo '[sg-compute] installing tmux + launching Claude...'
dnf install -y tmux
sudo -u ec2-user tmux new-session -d -s claude 'ollama run claude --model {model_name}'
echo 'tmux attach -t claude' > /etc/motd
'''


class Section__Claude_Launch(Type_Safe):

    def render(self, model_name: str, with_claude: bool = False) -> str:
        if not with_claude:
            return ''
        return TEMPLATE.format(model_name=model_name)
