# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Section__Ollama
# Bash fragment that installs Ollama, optionally rebinds it to 0.0.0.0:11434
# (for cross-node access — gated by the SG), and pulls the requested model.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

EXPOSE_API_OVERRIDE = '''\
mkdir -p /etc/systemd/system/ollama.service.d
cat > /etc/systemd/system/ollama.service.d/expose.conf << 'EOF'
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
EOF
systemctl daemon-reload
'''

TEMPLATE = '''\
# ── Ollama install ────────────────────────────────────────────────────────────
echo '[sg-compute] installing Ollama...'
curl -fsSL https://ollama.com/install.sh | sh
systemctl enable ollama
{expose_api_override}
systemctl restart ollama
sleep 5
echo '[sg-compute] waiting for Ollama API...'
until curl -sf http://localhost:11434/api/tags > /dev/null; do sleep 2; done
echo '[sg-compute] pulling model {model_name}...'
ollama pull {model_name}
echo '[sg-compute] model {model_name} ready'
'''


class Section__Ollama(Type_Safe):

    def render(self, model_name: str, expose_api: bool = False, pull_on_boot: bool = True) -> str:
        override = EXPOSE_API_OVERRIDE if expose_api else ''
        rendered = TEMPLATE.format(expose_api_override=override, model_name=model_name)
        if not pull_on_boot:
            rendered = rendered.replace(f'ollama pull {model_name}', f'echo "skipping pull (pull_on_boot=False) for {model_name}"')
        return rendered
