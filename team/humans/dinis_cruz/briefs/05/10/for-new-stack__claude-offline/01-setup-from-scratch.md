# Setup from scratch

End-to-end reproduction of a working local Claude Code stack on a fresh EC2 GPU instance. Aim: ~20 minutes from blank instance to executing `Bash(pwd)` against a local model, with sgit installed for stateful workflows.

## What you'll build

```
Laptop terminal
        │
        │ AWS SSM session
        ▼
EC2 g5.xlarge (NVIDIA A10G, 23 GiB)
  │
  ├── tmux session (survives SSM disconnects)
  │     ├── Claude Code (talks to local vLLM)
  │     └── sgit (encrypted vault sync to remote)
  │
  └── vLLM container (only container)
        ├── Qwen3-Coder-30B-A3B-Instruct-AWQ  (~16 GiB on GPU)
        ├── /v1/messages?beta=true              (Claude Code endpoint)
        ├── /v1/chat/completions, /v1/models    (verification endpoints)
        └── tool-call-parser=qwen3_coder        (the critical bit)
```

Container port binds to `127.0.0.1`. Nothing exposed to the internet. Access from the laptop is via SSM session only. Console workflow — no browser UI.

## Prerequisites

On your laptop:

- AWS CLI configured with credentials that can launch EC2 and start SSM sessions
- The Session Manager plugin for AWS CLI ([install guide](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html))
- A Hugging Face account (optional — only needed if you hit rate limits during model download)

In your AWS account:

- A VPC subnet that can reach the internet via NAT or IGW (for HF model downloads)
- An IAM role for EC2 with the `AmazonSSMManagedInstanceCore` managed policy attached
- A security group that allows outbound 443 (no inbound rules needed — SSM doesn't require open ingress)

## Step 1 — Launch the instance

| Setting | Value |
|---------|-------|
| AMI | Amazon Linux 2023 (latest), x86_64 |
| Instance type | `g5.xlarge` |
| Storage | 200 GiB gp3 (model cache + Docker images need room) |
| IAM role | One with `AmazonSSMManagedInstanceCore` attached |
| Security group | No inbound rules required |
| Purchasing option | Spot (cheaper, accept ~weekly interruption) or On-demand |

**Spot tip:** Set "Interruption behavior" to "stop" rather than "terminate" so the EBS volume (with the HF cache) survives. A replacement instance attached to the same volume warms vLLM from cache in ~2 minutes instead of redownloading 16 GiB.

Launch, wait for "Running", note the instance ID (referred to below as `$INSTANCE_ID`).

## Step 2 — Connect via SSM

From your laptop:

```bash
aws ssm start-session --region us-east-1 --target $INSTANCE_ID
```

You should land on `sh-5.2$`. From here on, all commands are on the EC2 instance unless explicitly noted.

## Step 3 — Base packages

A minimal toolset — no Open WebUI, no extras:

```bash
sudo dnf update -y
sudo dnf install -y docker git jq tmux python3.12 python3.12-pip
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
```

`tmux` is the one most people forget. Run Claude Code inside `tmux` and your session survives SSM disconnects, Wi-Fi blips, and laptop sleeps. Without it, every disconnect kills your conversation.

**Reconnect the SSM session** so the Docker group membership applies (otherwise you'll need `sudo` for every Docker command):

```bash
exit
# from laptop:
aws ssm start-session --region us-east-1 --target $INSTANCE_ID
```

Verify:

```bash
docker ps
nvidia-smi
```

Both should succeed. `nvidia-smi` should show the A10G with ~23028 MiB total memory.

## Step 4 — NVIDIA Container Toolkit

So Docker can pass the GPU through to containers:

```bash
curl -fsSL https://nvidia.github.io/libnvidia-container/stable/rpm/nvidia-container-toolkit.repo \
  | sudo tee /etc/yum.repos.d/nvidia-container-toolkit.repo

sudo dnf install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

Verify:

```bash
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
```

Should print the same `nvidia-smi` output as on the host.

## Step 5 — Start vLLM with the working configuration

This is the core of the setup. Save it as `~/bin/start-vllm.sh` so it's reproducible:

```bash
mkdir -p ~/bin ~/.cache/huggingface

cat > ~/bin/start-vllm.sh <<'BASH'
#!/usr/bin/env bash
set -euo pipefail

docker rm -f vllm-claude-code 2>/dev/null || true

docker run -d \
  --name vllm-claude-code \
  --gpus all \
  --ipc=host \
  --restart unless-stopped \
  -v "$HOME/.cache/huggingface:/root/.cache/huggingface" \
  -p 127.0.0.1:8000:8000 \
  vllm/vllm-openai:latest \
  --model QuantTrio/Qwen3-Coder-30B-A3B-Instruct-AWQ \
  --served-model-name local-coder \
  --host 0.0.0.0 \
  --port 8000 \
  --max-model-len 65536 \
  --max-num-seqs 1 \
  --gpu-memory-utilization 0.92 \
  --kv-cache-dtype fp8 \
  --enable-auto-tool-choice \
  --tool-call-parser qwen3_coder

echo "Waiting for vLLM to come up..."
until curl -sf http://127.0.0.1:8000/v1/models > /dev/null 2>&1; do
  sleep 5
  echo "  ... still loading (this takes ~2-3 minutes on first run, ~1 minute when cached)"
done
echo "vLLM is up: $(curl -s http://127.0.0.1:8000/v1/models | jq -r '.data[0].id')"
BASH

chmod +x ~/bin/start-vllm.sh
~/bin/start-vllm.sh
```

**Why each flag matters** (full discussion in `02-troubleshooting-and-tuning.md`):

| Flag | What goes wrong without it |
|------|----------------------------|
| `--tool-call-parser qwen3_coder` | Model emits structured tool calls; parser extracts them. Wrong parser → calls land in `content` as text and Claude Code can't execute. |
| `--enable-auto-tool-choice` | vLLM refuses to even accept a request with tools without this. |
| `--kv-cache-dtype fp8` | Halves KV cache memory cost per token. Without it, `--max-model-len 65536` won't fit in 23 GiB. |
| `--max-num-seqs 1` | We're a single user. Higher concurrency just steals KV budget. |
| `--gpu-memory-utilization 0.92` | Leaves ~1.8 GiB for non-cache GPU buffers. 0.95 is too aggressive on A10G. |
| `--ipc=host` | Required for vLLM's shared-memory tensor passing. |
| `--restart unless-stopped` | Survives spot reboots and Docker daemon restarts. |
| HF cache mount | Restarting the container does not redownload the 16 GiB model. |

**First-run download:** ~2 minutes for the model weights. Look for the "Maximum concurrency" line in the logs to confirm KV cache fits:

```bash
docker logs vllm-claude-code 2>&1 | grep -E 'Maximum concurrency|GPU KV cache size'
```

You want `Maximum concurrency for 65536 tokens per request: >= 1.0x`. If it's `< 1.0x`, see the OOM section in the troubleshooting doc.

## Step 6 — Verify tool calling works at the API level

Before installing Claude Code, prove the model is actually emitting structured tool calls. This single curl is worth the 60 seconds it takes:

```bash
curl -s http://127.0.0.1:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "local-coder",
    "messages": [{"role":"user","content":"What is the weather in Paris?"}],
    "tools": [{
      "type":"function",
      "function":{
        "name":"get_weather",
        "description":"Get weather for a location",
        "parameters":{"type":"object","properties":{"location":{"type":"string"}},"required":["location"]}
      }
    }],
    "tool_choice":"auto"
  }' | jq '.choices[0].message'
```

**Pass:**

```json
{
  "role": "assistant",
  "content": null,
  "tool_calls": [
    {
      "id": "chatcmpl-tool-...",
      "type": "function",
      "function": {
        "name": "get_weather",
        "arguments": "{\"location\": \"Paris\"}"
      }
    }
  ]
}
```

`content: null` and `tool_calls` populated. ✅ The parser is correctly extracting structured calls.

**Fail:**

```json
{
  "role": "assistant",
  "content": "I'll check the weather. {\"name\": \"get_weather\", \"arguments\": {\"location\": \"Paris\"}}",
  "tool_calls": []
}
```

JSON in `content`, empty `tool_calls`. ❌ Wrong parser for the model. Don't proceed; see `03-experiments-and-lessons.md` for the parser-mismatch debugging.

## Step 7 — Install sgit in a venv

`sgit` provides encrypted vault storage with Git-like semantics. This is what gives the ephemeral instance persistent memory — work happens in a vault, vault syncs to a remote, replacement instance pulls the vault and continues.

```bash
python3.12 -m venv ~/claude-session-venv
~/claude-session-venv/bin/pip install --upgrade pip
~/claude-session-venv/bin/pip install sgit
```

Verify:

```bash
~/claude-session-venv/bin/sgit --version
```

To use sgit from any shell, either activate the venv (`source ~/claude-session-venv/bin/activate`) or call the binary directly. We'll add the activation to a project `CLAUDE.md` later so Claude Code knows about it.

## Step 8 — Install Claude Code

```bash
curl -fsSL https://claude.ai/install.sh | bash
```

Verify:

```bash
claude --version
```

Should print `2.1.x` or newer.

## Step 9 — Configure Claude Code for the local backend

This is where most setups silently break. **Three things have to be right:**

1. The launcher script with environment variables
2. `~/.claude/settings.json` with the env block
3. (Optional but recommended) Skip permission prompts if you're on a disposable instance

### Launcher script

```bash
cat > ~/local-llm-claude.sh <<'SH'
#!/usr/bin/env bash
set -euo pipefail

# Point Claude Code at the local vLLM
export ANTHROPIC_BASE_URL="http://127.0.0.1:8000"
export ANTHROPIC_API_KEY="dummy"
export ANTHROPIC_AUTH_TOKEN="dummy"

# Map every Claude Code model alias to our local model
export ANTHROPIC_MODEL="local-coder"
export ANTHROPIC_DEFAULT_OPUS_MODEL="local-coder"
export ANTHROPIC_DEFAULT_SONNET_MODEL="local-coder"
export ANTHROPIC_DEFAULT_HAIKU_MODEL="local-coder"
export ANTHROPIC_SMALL_FAST_MODEL="local-coder"

# Discovery + traffic-reduction flags
export CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY=1
export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
export DISABLE_AUTOUPDATER=1
export CLAUDE_CODE_DISABLE_OFFICIAL_MARKETPLACE_AUTOINSTALL=1
export CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1
export CLAUDE_CODE_MAX_OUTPUT_TOKENS=1024

# On a disposable instance, you can skip the "allow this Bash command?" prompts
# by adding --dangerously-skip-permissions. Default below is safe; uncomment to enable.
# exec claude --dangerously-skip-permissions "$@"
exec claude "$@"
SH

chmod +x ~/local-llm-claude.sh
```

### Settings file

`~/.claude/settings.json` controls the env vars that **must** be set there (export does not work for these — see Lesson 4 in `03-experiments-and-lessons.md`):

```bash
mkdir -p ~/.claude

cat > ~/.claude/settings.json <<'JSON'
{
  "theme": "auto",
  "env": {
    "CLAUDE_CODE_ATTRIBUTION_HEADER": "0",
    "CLAUDE_CODE_DISABLE_1M_CONTEXT": "1",
    "CONTEXT_WINDOW_OVERRIDE": "65536",
    "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": "70"
  }
}
JSON
```

**What each one does:**

| Variable | Effect |
|----------|--------|
| `CLAUDE_CODE_ATTRIBUTION_HEADER=0` | Stops Claude Code from injecting a per-request hash that invalidates vLLM's prefix cache. ~90% speedup on subsequent turns. |
| `CLAUDE_CODE_DISABLE_1M_CONTEXT=1` | Stops Claude Code from claiming "1M context" in the `[1m]` model badge. |
| `CONTEXT_WINDOW_OVERRIDE=65536` | Tells Claude Code the real ceiling, so `/context` shows accurate usage percentage. |
| `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=70` | Fires `/compact` at 70% (~45k tokens), leaving room for the compact request itself to fit. |

If `~/.claude/settings.json` already exists, merge with `jq`:

```bash
jq '. + {
  "env": ((.env // {}) + {
    "CLAUDE_CODE_ATTRIBUTION_HEADER": "0",
    "CLAUDE_CODE_DISABLE_1M_CONTEXT": "1",
    "CONTEXT_WINDOW_OVERRIDE": "65536",
    "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": "70"
  })
}' ~/.claude/settings.json > ~/.claude/settings.json.tmp \
&& mv ~/.claude/settings.json.tmp ~/.claude/settings.json
```

## Step 10 — Launch in tmux

This step is small but high-value. Run Claude Code inside a `tmux` session and your conversation survives SSM disconnects:

```bash
tmux new -s claude
# inside tmux:
~/local-llm-claude.sh
```

If your SSM session drops, reconnect and:

```bash
tmux attach -t claude
```

You're back exactly where you left off, mid-conversation, with full context preserved.

## Step 11 — Verify with the canonical test

The Claude Code banner should show `local-coder · API Usage Billing`. Run:

```
Use the Bash tool to run: pwd
```

**Pass:**

```
● I'll use the Bash tool to check the current working directory.
● Bash(pwd)
  ⎿  /home/ssm-user
```

The `● Bash(pwd)` line means a structured tool call was extracted, dispatched, and executed; the actual directory came back. ✅

**Fail:**

```
● Sure, I'll use the Bash tool to run the pwd command:
  {
    "name": "Bash",
    "arguments": { "command": "pwd" }
  }
```

JSON shown as plain text, no `Bash(...)` indicator, no output. ❌ The parser isn't extracting tool calls. Re-check the vLLM startup flags.

## Step 12 — Confirm the context display is honest

Inside Claude Code:

```
/context
```

Should show `local-coder · 22.4k/65k tokens (34%)` or similar — the absolute number is real, the percentage matches reality. If you still see `[1m]` and "(2%)" the env vars in `~/.claude/settings.json` aren't being picked up. Quit Claude Code (`/exit`), re-check the settings file, and relaunch.

## Step 13 — Optional: confirm spot survival

Stop the instance:

```bash
# from laptop
aws ec2 stop-instances --region us-east-1 --instance-ids $INSTANCE_ID
aws ec2 wait instance-stopped --region us-east-1 --instance-ids $INSTANCE_ID
aws ec2 start-instances --region us-east-1 --instance-ids $INSTANCE_ID
aws ec2 wait instance-running --region us-east-1 --instance-ids $INSTANCE_ID
```

Reconnect via SSM. Because of `--restart unless-stopped`, Docker should bring vLLM back automatically. If not:

```bash
~/bin/start-vllm.sh
```

vLLM warms from the local HF cache in ~60-90 seconds (no 116-second download). `tmux attach -t claude` to resume your session, or start a fresh one with `~/local-llm-claude.sh`.

## Total time check

On a fresh instance, end-to-end:

| Step | Time |
|------|------|
| Launch + boot + first SSM connect | ~3 min |
| Steps 3-4 (Docker + NVIDIA toolkit) | ~3 min |
| Step 5 first run (model download) | ~2-3 min |
| Steps 6-12 (verify, install sgit + Claude Code, configure) | ~5 min |
| **Total** | **~15 min** |

On a recovered instance with cache intact:

| Step | Time |
|------|------|
| Boot + reconnect | ~1 min |
| `~/bin/start-vllm.sh` (cache warm) | ~90 sec |
| `tmux attach` or fresh `~/local-llm-claude.sh` | seconds |
| **Total** | **~3 min** |

That's the spot-resilience payoff — a reclaimed instance is back in working order in three minutes if you keep the EBS volume.

## Quick health check (run anytime)

```bash
cat > ~/bin/vllm-status.sh <<'BASH'
#!/usr/bin/env bash
echo "=== Container ==="
docker ps --filter name=vllm-claude-code --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
echo
echo "=== GPU ==="
nvidia-smi --query-gpu=memory.used,memory.free,memory.total,utilization.gpu --format=csv,noheader
echo
echo "=== Model ==="
curl -s http://127.0.0.1:8000/v1/models | jq -r '.data[0] | "id: \(.id)\nmax_model_len: \(.max_model_len)"' 2>/dev/null || echo "vLLM not responding"
echo
echo "=== Recent throughput ==="
docker logs --tail 200 vllm-claude-code 2>&1 | grep -E 'KV cache usage|Prefix cache' | tail -3
BASH
chmod +x ~/bin/vllm-status.sh
```

Then `~/bin/vllm-status.sh` whenever something feels off. (For an AMI build, this is also useful as a login-time MOTD — see `05-ami-publishing.md`.)

## Optional: a project CLAUDE.md for sgit workflows

If you'll be using Claude Code primarily to drive sgit-based work, a `CLAUDE.md` in your working directory primes the model with the activation incantation and avoids re-discovery on each session:

```bash
cat > ~/CLAUDE.md <<'MD'
# Project guidelines

## sgit
sgit is installed in `~/claude-session-venv`. Always activate the venv first:
`source ~/claude-session-venv/bin/activate`

Common commands:
- `sgit status` — check vault sync state ("ahead/behind" tells next action)
- `sgit commit` — bare command, no `-m` flag; commits staged changes
- `sgit push` / `sgit pull` — sync with remote; pull first if diverged
- `sgit vault info` — vault key, read key, web URL

Workflow:
1. Check status before any operation
2. Commit before push (sgit refuses dirty pushes)
3. Pull before push if status shows divergence

## Verbose commands
When running package installation or other commands with verbose output,
pipe through `tail -20` or redirect to /tmp/install.log and only read the
relevant lines. Keep tool output short to preserve context budget.

## File reading
When reading large files, use offset and limit parameters rather than
reading the whole file at once.
MD
```

100 tokens of guidance saves thousands later, and is the difference between Claude Code rediscovering the venv path every session vs. just using it.
