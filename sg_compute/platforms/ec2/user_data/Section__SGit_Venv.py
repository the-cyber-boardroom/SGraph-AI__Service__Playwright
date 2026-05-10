# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Section__SGit_Venv
# Installs sgit in a Python 3.13 venv under ~/claude-session-venv for ssm-user.
# sgit requires Python ≥ 3.13. The DLAMI defaults to python3.9; python3.13 must
# be installed explicitly from AL2023 repos. There is no separate python3.13-pip
# package — pip ships bundled inside the python3.13 package on AL2023. All pip
# calls inside the venv use `python3.13 -m pip` to guarantee the correct
# interpreter is used regardless of PATH or default-python symlinks.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

VENV = '/home/ssm-user/claude-session-venv'

TEMPLATE = '''\
# ── sgit venv (python3.13) ────────────────────────────────────────────────────
echo '[sg-compute] waiting for ssm-user...'
until id ssm-user >/dev/null 2>&1; do sleep 2; done
echo '[sg-compute] installing python3.13 (pip is bundled, no separate package)...'
dnf install -y python3.13
echo "[sg-compute] python version: $(python3.13 --version)"
sudo -u ssm-user python3.13 -m venv {venv}
echo '[sg-compute] upgrading pip in venv...'
sudo -u ssm-user {venv}/bin/python3.13 -m pip install --quiet --upgrade pip
echo '[sg-compute] installing sgit...'
sudo -u ssm-user {venv}/bin/python3.13 -m pip install --quiet sgit
echo "[sg-compute] sgit ready: $(sudo -u ssm-user {venv}/bin/sgit --version 2>/dev/null || echo installed)"
'''.format(venv=VENV)


class Section__SGit_Venv(Type_Safe):

    def render(self) -> str:
        return TEMPLATE

