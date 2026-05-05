# ═══════════════════════════════════════════════════════════════════════════════
# Ephemeral EC2 — Open_Design__User_Data__Builder
# Assembles the cloud-init bash script for an Open Design EC2 instance.
# Section order: Base → Docker → Node → Env → [Clone+Build] → Systemd → [Claude] → Nginx → Shutdown
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute.platforms.ec2.user_data.Section__Base      import Section__Base
from sg_compute.platforms.ec2.user_data.Section__Docker    import Section__Docker
from sg_compute.platforms.ec2.user_data.Section__Env__File import Section__Env__File
from sg_compute.platforms.ec2.user_data.Section__Nginx     import Section__Nginx
from sg_compute.platforms.ec2.user_data.Section__Node      import Section__Node
from sg_compute.platforms.ec2.user_data.Section__Shutdown  import Section__Shutdown
from sg_compute.platforms.ec2.user_data.Section__Sidecar   import Section__Sidecar

CLONE_AND_BUILD = '''
# ── Clone and build Open Design ───────────────────────────────────────────────
echo "[open-design] cloning ref={ref}..."
git clone --depth 1 https://github.com/nexu-io/open-design /opt/open-design 2>/dev/null || true
cd /opt/open-design
git fetch --depth 1 origin {ref} 2>/dev/null && git checkout FETCH_HEAD 2>/dev/null || true

echo "[open-design] installing dependencies (this takes a few minutes)..."
pnpm install --frozen-lockfile 2>/dev/null || pnpm install

echo "[open-design] building web app..."
pnpm --filter @open-design/web build

echo "[open-design] build complete"
'''

SYSTEMD_UNIT = '''
# ── Open Design systemd service ───────────────────────────────────────────────
cat > /etc/systemd/system/open-design.service <<'UNITEOF'
[Unit]
Description=Open Design daemon
After=network.target

[Service]
EnvironmentFile=/run/{stack_name}/env
WorkingDirectory=/opt/open-design
ExecStart=/usr/bin/node apps/daemon/dist/index.js --port 7456
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
UNITEOF
systemctl daemon-reload
systemctl enable --now open-design
echo "[open-design] daemon started"
'''

CLAUDE_CLI = '''
# ── Claude CLI ────────────────────────────────────────────────────────────────
echo "[open-design] installing claude CLI (detected api_key)..."
npm install -g @anthropic-ai/claude-code
echo "[open-design] claude CLI installed — ANTHROPIC_API_KEY will be picked up from env"
'''

FOOTER = '\necho "[ephemeral-ec2] open-design boot complete at $(date -u +%FT%TZ)"\n'


class Open_Design__User_Data__Builder(Type_Safe):

    def render(self, stack_name     : str  ,
                     region         : str  ,
                     api_key        : str  = '',
                     ollama_base_url: str  = '',
                     open_design_ref: str  = 'main',
                     fast_boot      : bool = False ,
                     max_hours      : int  = 1     ,
                     registry       : str  = ''    ,
                     api_key_name   : str  = 'X-API-Key',
                     api_key_ssm_path  : str  = ''    ) -> str:
        parts = []
        parts.append(Section__Base().render(stack_name=stack_name))
        parts.append(Section__Docker().render())
        parts.append(Section__Node().render())

        env_lines = ['OD_PORT=7456']
        if api_key:
            env_lines.append(f'ANTHROPIC_API_KEY={api_key}')
        if ollama_base_url:
            env_lines.append(f'OLLAMA_BASE_URL={ollama_base_url}')
        parts.append(Section__Env__File().render(
            stack_name  = stack_name           ,
            env_content = '\n'.join(env_lines) ))

        if not fast_boot:
            parts.append(CLONE_AND_BUILD.format(ref=open_design_ref))

        parts.append(SYSTEMD_UNIT.format(stack_name=stack_name))

        if api_key:
            parts.append(CLAUDE_CLI)

        parts.append(Section__Nginx().render(app_port=7456))

        sidecar = Section__Sidecar().render(registry      = registry      ,
                                            api_key_name  = api_key_name  ,
                                            api_key_ssm_path = api_key_ssm_path )
        if sidecar:
            parts.append(sidecar)

        if max_hours > 0:
            parts.append(Section__Shutdown().render(max_hours=max_hours))

        parts.append(FOOTER)
        return '\n'.join(parts)
