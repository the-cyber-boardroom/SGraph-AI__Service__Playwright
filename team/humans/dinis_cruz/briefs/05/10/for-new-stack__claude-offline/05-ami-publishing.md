# Publishing as an AWS AMI

How to bake the working stack from `01-setup-from-scratch.md` into a reusable Amazon Machine Image, with licensing notes for the various components and a clean cleanup checklist before snapshotting.

## What goes in the AMI vs. what doesn't

The headline rule: **bundle everything that's freely redistributable, install Claude Code on first boot.** This keeps each user's relationship with Anthropic direct, which is the licensing-clean path.

### Bundled in the AMI

| Component | License | Notes |
|-----------|---------|-------|
| Amazon Linux 2023 base | AWS-provided | Source AMI; AWS handles licensing |
| Docker | Apache 2.0 | OK |
| NVIDIA Container Toolkit | Apache 2.0 | OK |
| `vllm/vllm-openai` Docker image | Apache 2.0 | Pin to a specific digest, not `:latest` |
| Hugging Face cache: Qwen3-Coder-30B-A3B-Instruct-AWQ weights | Apache 2.0 (Qwen3-Coder); third-party AWQ requant | Verify the AWQ repo's LICENSE; QuantTrio inherits Apache 2.0 in our case |
| Python 3.12 + venv with `sgit` | sgit's own license | Verify sgit's license before redistributing; if MIT/Apache, fine |
| `tmux`, `git`, `jq` | OSS standard | OK |
| Launcher scripts (`local-llm-claude.sh`, `start-vllm.sh`, `vllm-status.sh`) | Yours | OK |
| `~/.claude/settings.json` (env vars only) | Yours | **No credentials, no auth tokens** |
| First-boot systemd service that installs Claude Code | Yours | OK |

### Installed on first boot (by the user, from upstream)

| Component | License | Why |
|-----------|---------|-----|
| Claude Code | Proprietary (`© Anthropic PBC. All rights reserved.`) | Cannot be redistributed. Each user must install it themselves; the AMI orchestrates this on their behalf so they accept Anthropic's terms directly. |

### Excluded entirely

| Component | Reason |
|-----------|--------|
| Open WebUI | Not needed for a console-based workflow; some license restrictions on redistribution as part of branded products |
| LiteLLM proxy | Not needed (vLLM has native Anthropic Messages support) |
| Any Anthropic credentials, API keys, OAuth tokens | Never bundle these — security and licensing both |
| Test data, vault contents, conversation history | Privacy + cleanliness |

## License rundown — what you can say in the listing

Best phrased plainly:

> This AMI bundles open-source software (vLLM, Apache 2.0; Qwen3-Coder model weights, Apache 2.0; sgit; standard system utilities). It is configured to host a local LLM inference server compatible with the Anthropic Messages API.
>
> Claude Code is **not** bundled. On first boot, the instance runs Anthropic's official installer (`https://claude.ai/install.sh`) to install Claude Code into the user's home directory. Use of Claude Code is governed by Anthropic's [Commercial Terms of Service](https://www.anthropic.com/legal/commercial-terms). Local model routing via `ANTHROPIC_BASE_URL` does not relieve the user of those terms.
>
> This AMI does not include any Anthropic API credentials, authentication tokens, or session state.

That phrasing accomplishes three things: it sets expectations, names the open-source licenses honestly, and makes clear the Claude Code relationship is between the user and Anthropic.

## Bake script — what to run during AMI build

This script brings a fresh Amazon Linux 2023 instance to a state ready for snapshotting (minus the cleanup step, which is a separate script).

```bash
cat > ~/bake-setup.sh <<'BASH'
#!/usr/bin/env bash
# Run this once on a fresh AL2023 instance during AMI build.
# Idempotent: safe to re-run.
set -euo pipefail

echo "=== Phase 1: base packages ==="
sudo dnf update -y
sudo dnf install -y docker git jq tmux python3.12 python3.12-pip
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"

echo "=== Phase 2: NVIDIA Container Toolkit ==="
curl -fsSL https://nvidia.github.io/libnvidia-container/stable/rpm/nvidia-container-toolkit.repo \
  | sudo tee /etc/yum.repos.d/nvidia-container-toolkit.repo
sudo dnf install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

echo "=== Phase 3: pull and pin vLLM image ==="
docker pull vllm/vllm-openai:latest
VLLM_DIGEST=$(docker inspect vllm/vllm-openai:latest --format='{{index .RepoDigests 0}}')
echo "Pinned vLLM digest: $VLLM_DIGEST"
echo "$VLLM_DIGEST" > ~/.vllm-pinned-digest

echo "=== Phase 4: pre-download model weights ==="
mkdir -p ~/.cache/huggingface
# Run vLLM briefly to trigger the weights download into the cache mount
timeout 600 docker run --rm --gpus all --ipc=host \
  -v "$HOME/.cache/huggingface:/root/.cache/huggingface" \
  "$VLLM_DIGEST" \
  --model QuantTrio/Qwen3-Coder-30B-A3B-Instruct-AWQ \
  --max-model-len 4096 \
  --enforce-eager \
  --port 8000 &
VLLM_PID=$!
# Wait for the cache to populate (model download completes when vLLM starts serving)
until curl -sf http://127.0.0.1:8000/v1/models > /dev/null 2>&1; do
  sleep 10
  echo "  ...waiting for model download to complete"
  if ! kill -0 $VLLM_PID 2>/dev/null; then
    echo "vLLM exited; check logs"
    exit 1
  fi
done
echo "Model downloaded. Stopping warm-up vLLM..."
kill $VLLM_PID 2>/dev/null || true
wait $VLLM_PID 2>/dev/null || true

echo "=== Phase 5: Python venv with sgit ==="
python3.12 -m venv ~/claude-session-venv
~/claude-session-venv/bin/pip install --upgrade pip
~/claude-session-venv/bin/pip install sgit

echo "=== Phase 6: launcher scripts ==="
mkdir -p ~/bin

# start-vllm.sh — uses pinned digest from Phase 3
cat > ~/bin/start-vllm.sh <<'INNER'
#!/usr/bin/env bash
set -euo pipefail
VLLM_IMAGE=$(cat ~/.vllm-pinned-digest 2>/dev/null || echo "vllm/vllm-openai:latest")
docker rm -f vllm-claude-code 2>/dev/null || true
docker run -d \
  --name vllm-claude-code \
  --gpus all \
  --ipc=host \
  --restart unless-stopped \
  -v "$HOME/.cache/huggingface:/root/.cache/huggingface" \
  -p 127.0.0.1:8000:8000 \
  "$VLLM_IMAGE" \
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
echo "vLLM starting (give it ~60-90s to warm from cache)..."
INNER

# vllm-status.sh
cat > ~/bin/vllm-status.sh <<'INNER'
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
INNER

# local-llm-claude.sh — safe default (no --dangerously-skip-permissions)
cat > ~/local-llm-claude.sh <<'INNER'
#!/usr/bin/env bash
set -euo pipefail
export ANTHROPIC_BASE_URL="http://127.0.0.1:8000"
export ANTHROPIC_API_KEY="dummy"
export ANTHROPIC_AUTH_TOKEN="dummy"
export ANTHROPIC_MODEL="local-coder"
export ANTHROPIC_DEFAULT_OPUS_MODEL="local-coder"
export ANTHROPIC_DEFAULT_SONNET_MODEL="local-coder"
export ANTHROPIC_DEFAULT_HAIKU_MODEL="local-coder"
export ANTHROPIC_SMALL_FAST_MODEL="local-coder"
export CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY=1
export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
export DISABLE_AUTOUPDATER=1
export CLAUDE_CODE_DISABLE_OFFICIAL_MARKETPLACE_AUTOINSTALL=1
export CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1
export CLAUDE_CODE_MAX_OUTPUT_TOKENS=1024
exec claude "$@"
INNER

chmod +x ~/bin/start-vllm.sh ~/bin/vllm-status.sh ~/local-llm-claude.sh

echo "=== Phase 7: Claude Code settings.json ==="
mkdir -p ~/.claude
cat > ~/.claude/settings.json <<'INNER'
{
  "theme": "auto",
  "env": {
    "CLAUDE_CODE_ATTRIBUTION_HEADER": "0",
    "CLAUDE_CODE_DISABLE_1M_CONTEXT": "1",
    "CONTEXT_WINDOW_OVERRIDE": "65536",
    "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": "70"
  }
}
INNER

echo "=== Phase 8: first-boot Claude Code install systemd service ==="
sudo tee /etc/systemd/system/claude-code-firstboot.service > /dev/null <<'INNER'
[Unit]
Description=Install Claude Code on first boot (per-instance, license-clean)
ConditionPathExists=!/var/lib/claude-code-installed
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=ssm-user
Group=ssm-user
ExecStart=/bin/bash -lc 'curl -fsSL https://claude.ai/install.sh | bash && sudo touch /var/lib/claude-code-installed'
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
INNER

sudo systemctl daemon-reload
sudo systemctl enable claude-code-firstboot.service
# Do NOT start it during bake — it will run on first boot of an instance launched from the AMI

echo "=== Phase 9: login MOTD ==="
sudo tee /etc/profile.d/local-claude-motd.sh > /dev/null <<'INNER'
#!/usr/bin/env bash
# Show health status when an interactive user logs in
if [[ $- == *i* ]] && [[ -x ~/bin/vllm-status.sh ]]; then
  echo
  echo "Local Claude Code AMI — quick status"
  echo "------------------------------------"
  ~/bin/vllm-status.sh
  echo
  echo "Start vLLM:    ~/bin/start-vllm.sh"
  echo "Launch Claude: tmux new -s claude    (then ~/local-llm-claude.sh inside)"
  echo
fi
INNER
sudo chmod +x /etc/profile.d/local-claude-motd.sh

echo "=== Bake setup complete ==="
echo "Next step: run ~/bake-cleanup.sh, then create the AMI snapshot."
BASH

chmod +x ~/bake-setup.sh
```

Run it once on a fresh instance:

```bash
~/bake-setup.sh
```

## Cleanup script — what to scrub before snapshotting

Two things matter here: removing anything sensitive (credentials, history, identity) and removing per-instance state that would create problems if duplicated across many launched instances (SSH host keys, cloud-init data, machine-id).

```bash
cat > ~/bake-cleanup.sh <<'BASH'
#!/usr/bin/env bash
# Run this last, immediately before creating the AMI snapshot.
set -euo pipefail

echo "=== 1. Remove any test Claude Code installation ==="
rm -f /usr/local/bin/claude ~/.local/bin/claude 2>/dev/null
rm -rf ~/.claude/projects ~/.claude/conversations ~/.claude/.credentials* 2>/dev/null
# Keep ~/.claude/settings.json — env vars are part of the AMI

echo "=== 2. Remove session state from sgit and other tools ==="
rm -rf ~/.cache/sgit ~/.config/sgit 2>/dev/null
find ~ -type d -name '.sg_vault' -exec rm -rf {} + 2>/dev/null || true
rmdir ~/_vaults 2>/dev/null || true

echo "=== 3. Wipe shell history ==="
rm -f ~/.bash_history ~/.zsh_history
history -c || true

echo "=== 4. Stop containers (keep images and HF cache) ==="
docker rm -f vllm-claude-code 2>/dev/null || true
docker container prune -f
# IMPORTANT: do NOT prune images or volumes — that would remove the model weights

echo "=== 5. Confirm the model weights are still present ==="
if ! ls ~/.cache/huggingface/hub/models--QuantTrio--Qwen3-Coder-30B-A3B-Instruct-AWQ 2>/dev/null; then
  echo "WARNING: Model weights missing from HF cache. Did Phase 4 of bake-setup complete?"
  exit 1
fi

echo "=== 6. Wipe AWS-instance identity (CRITICAL) ==="
# Without this, every AMI-launched instance gets the same SSH host key (security hole)
# and reuses cloud-init state from the bake instance.
sudo rm -rf /var/lib/cloud/instances/* /var/lib/cloud/instance 2>/dev/null
sudo rm -f /etc/ssh/ssh_host_* 2>/dev/null
sudo rm -f /etc/machine-id
sudo touch /etc/machine-id

echo "=== 7. Wipe systemd journal ==="
sudo journalctl --rotate
sudo journalctl --vacuum-time=1s

echo "=== 8. Clean dnf cache ==="
sudo dnf clean all

echo "=== 9. Truncate logs ==="
sudo find /var/log -type f -exec truncate -s 0 {} \; 2>/dev/null || true

echo "=== 10. Final secrets scan ==="
echo "Scanning for accidentally-left credentials..."
HITS=$(sudo grep -RiE '(api[_-]?key|token|secret|password|sk-[a-z]+-)[=:]' \
  /home/ssm-user /etc /root 2>/dev/null \
  | grep -v -E '(dummy|placeholder|example|YOUR-|ENV_VAR_NAME)' \
  | head -20 || true)
if [[ -n "$HITS" ]]; then
  echo "WARNING — possible credential leakage found:"
  echo "$HITS"
  echo "Review and clean before snapshotting."
  exit 1
fi
echo "Secrets scan clean."

echo
echo "=== Cleanup complete ==="
echo "You may now create the AMI snapshot."
echo "From your laptop:"
echo "  aws ec2 create-image --instance-id <INSTANCE_ID> --name 'local-claude-code-vN' --no-reboot"
BASH

chmod +x ~/bake-cleanup.sh
```

The secrets scan at step 10 has saved me from publishing API keys more than once. Trust the alarm.

## Creating the AMI

After `bake-setup.sh` and `bake-cleanup.sh`, snapshot from your laptop:

```bash
aws ec2 create-image \
  --region us-east-1 \
  --instance-id $INSTANCE_ID \
  --name "local-claude-code-v1" \
  --description "Local Claude Code: vLLM + Qwen3-Coder + sgit on g5.xlarge" \
  --no-reboot
```

The `--no-reboot` flag means AWS doesn't restart the instance during the snapshot. Safer for our case because the cleanup script left the instance in a known-good but un-rebooted state.

The snapshot takes ~10-15 minutes for a 200 GiB volume. Wait for the AMI to reach `available` state:

```bash
aws ec2 describe-images --owners self --image-ids $AMI_ID --query 'Images[0].State'
```

## Verifying the AMI works

Critical: launch a fresh instance from the AMI in a different VPC or with a different IAM role, and verify end-to-end:

```bash
# Launch
aws ec2 run-instances \
  --region us-east-1 \
  --image-id $AMI_ID \
  --instance-type g5.xlarge \
  --iam-instance-profile Name=$INSTANCE_PROFILE \
  --instance-market-options 'MarketType=spot' \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=ami-test}]'
```

After it boots:

```bash
aws ssm start-session --target $NEW_INSTANCE_ID

# Once connected, verify on the instance:
~/bin/vllm-status.sh         # should show vLLM running (auto-started via --restart unless-stopped)
ls /var/lib/claude-code-installed  # should exist (firstboot service ran)
which claude                  # should print path
~/local-llm-claude.sh
# Try the canonical test:
> Use the Bash tool to run: pwd
```

If `~/bin/vllm-status.sh` shows vLLM not running, the `--restart unless-stopped` may not have triggered on first boot. Run `~/bin/start-vllm.sh` manually and confirm.

If `claude` is not on PATH, the firstboot service didn't run or hasn't finished. Check:

```bash
sudo systemctl status claude-code-firstboot.service
sudo journalctl -u claude-code-firstboot.service
```

Most likely cause: no internet route at boot. Verify the subnet has NAT/IGW.

## Three publishing tiers, ranked by effort

### Tier 1: Private to your account

```bash
# Already done — the AMI defaults to private
aws ec2 describe-images --image-ids $AMI_ID
```

Use it yourself, share with specific account IDs:

```bash
aws ec2 modify-image-attribute \
  --image-id $AMI_ID \
  --launch-permission "Add=[{UserId=111122223333}]"
```

**Effort:** zero beyond what you've done. **Recommended starting point.**

### Tier 2: Public AMI (not via Marketplace)

Make the AMI publicly launchable but not listed in Marketplace:

```bash
aws ec2 modify-image-attribute \
  --image-id $AMI_ID \
  --launch-permission "Add=[{Group=all}]"
```

Anyone with the AMI ID can launch it; it doesn't appear in Marketplace search. No fee, no review. Document the AMI ID and instructions in a public GitHub repo (link this doc set).

**Considerations:**
- All the licensing safeguards above must be in place (no bundled Claude Code, no credentials, etc.)
- AWS still requires the AMI to comply with their general AMI policies even if not in Marketplace
- You're responsible for ongoing security updates; users who launch it inherit whatever vulnerabilities are in the bake

**Effort:** small. **Reasonable for a community-friendly publication.**

### Tier 3: AWS Marketplace listing

Substantial work. Requires:

- AWS Marketplace seller account registration and identity verification
- Submission of the AMI for AWS security review (they scan for common issues, malware, exposed credentials)
- Compliance with [AMI-based product requirements](https://docs.aws.amazon.com/marketplace/latest/userguide/product-and-ami-policies.html), including:
  - No hardcoded IPs, credentials, account IDs
  - First-boot configuration via cloud-init or systemd (you already have this)
  - Documented patching/update strategy
  - Standard EC2 instance type compatibility tests
- Pricing model (free, hourly, or contract)
- End-user license agreement (EULA) text
- Listing copy, screenshots, support contact

**Pricing implication:** if listing as "free," still possible. If listing with a fee, AWS takes a cut and you take on tax/billing obligations.

**The Claude Code redistribution issue must be airtight at this tier.** Marketplace reviewers will examine the listing copy. The phrasing in the [License rundown](#license-rundown--what-you-can-say-in-the-listing) section above is what should appear in your listing.

**Effort:** weeks of preparation, days of review, ongoing maintenance. **Not worth it for personal/community use.** Worth it for a commercial offering or supported enterprise product.

## What to put in the Marketplace listing notes

If you go to Tier 3, your listing copy should include:

```
## What this AMI provides

A pre-configured EC2 environment for running a local large language model
inference server (vLLM) optimized for agentic CLI workflows. Includes:

- vLLM container, pre-pulled and pinned
- Qwen3-Coder-30B-A3B-Instruct-AWQ model weights, pre-cached
- Python virtual environment with sgit (encrypted vault sync)
- Helper scripts for starting the LLM server and checking status
- tmux for resilient SSH/SSM sessions

## Software licenses

This AMI bundles open-source software:
- vLLM: Apache License 2.0
- Qwen3-Coder model: Apache License 2.0
- sgit: <verify and state license>
- Standard system utilities under their respective licenses

## Claude Code (installed on first boot)

This AMI does not include Claude Code. On first boot, the instance runs
Anthropic's official installer to install Claude Code from upstream
(claude.ai). Use of Claude Code is governed by Anthropic's Commercial
Terms of Service: https://www.anthropic.com/legal/commercial-terms

The AMI configures Claude Code to route requests to the local vLLM server
running on the instance via the ANTHROPIC_BASE_URL environment variable.
This is a documented, supported Claude Code configuration option.

## What this AMI does not provide

- Anthropic API credentials or tokens (you do not need them for local routing,
  but Claude Code may prompt for an account on first launch)
- Production-grade hardening or multi-user access controls
- Automatic updates to the bundled vLLM image or model weights
- Web search or other Anthropic-hosted "server tools" (these require
  Anthropic's hosted API and are not supported via local routing)

## Recommended use

- Single-user development workflows on a private GPU instance
- Air-gapped or privacy-sensitive coding tasks
- Cost-conscious heavy Claude Code usage where API spend is the constraint

## Not recommended for

- Multi-user team development
- Production application backends
- Workloads requiring Anthropic's hosted-only features (web search, etc.)

## Recommended instance type

g5.xlarge (NVIDIA A10G, 24 GiB VRAM). The AMI is sized for this instance
type and will not work on smaller GPU instances. Larger instance types
(g5.2xlarge, g5.4xlarge, g6e.xlarge) work but use the same model
configuration unless modified.
```

## Iteration workflow once the AMI exists

When you update the configuration (new vLLM version, different model, additional tools), the cycle is:

1. Launch a fresh instance from the **previous version** of the AMI
2. Make the changes you want
3. Re-run `~/bake-cleanup.sh`
4. Snapshot → new AMI version
5. Verify via Tier 1 launch
6. Optionally update permissions / Marketplace listing

Keep old AMI versions around for rollback. They're cheap to retain (snapshots are deduplicated at the EBS layer).

## Cost notes for users

Make sure your listing or README is honest about what users will pay AWS:

| Item | Approximate cost |
|------|------------------|
| `g5.xlarge` on-demand, us-east-1 | ~$1.00/hour |
| `g5.xlarge` spot, us-east-1 | ~$0.30–0.50/hour |
| 200 GiB gp3 EBS volume | ~$0.02/hour ($16/month) |
| Outbound data | Standard EC2 rates; minimal in this use case |

For a user running 4 hours/day on spot: ~$60–80/month all-in. Compare to a Claude Code Max plan ($100–200/month). This is the financial pitch.

## A note about the alternative — first-boot model download instead of bundled

You can build a "thin AMI" that does *not* bundle the 16 GiB of model weights, and instead downloads them on first boot:

**Pros:**
- Smaller AMI, faster to copy across regions
- Always pulls the latest model revision
- No HF redistribution question (though Apache 2.0 makes this trivial anyway)

**Cons:**
- First-boot delay extends from ~10 seconds (Claude Code install) to ~3 minutes (model download + Claude Code install)
- User pays for the network egress on first boot (or ingress if they're on a different cloud)
- If HF is rate-limiting or down, the instance is broken

**Recommendation:** bundle the model. The AMI is bigger but the user experience is dramatically better, and the licensing is unambiguous (Apache 2.0). If you're really concerned about AMI size, build a "core" AMI without the model and a "fat" AMI with it, and let users pick.

## Common pitfalls

- **Forgot `--no-reboot`** during AMI creation, and the instance auto-restarts from a state that no longer has cleanup applied. Always use `--no-reboot` after running cleanup.
- **Bundling the SSH host keys** because you forgot to remove `/etc/ssh/ssh_host_*`. Every launched instance will have the same host key, which is a real security issue. Step 6 of `bake-cleanup.sh` handles this.
- **Bundling a Claude Code session**. If you tested Claude Code during bake, the credentials might be in `~/.claude/.credentials*`. Step 1 of `bake-cleanup.sh` handles this.
- **Pinning `vllm:latest`** instead of a digest. A user launching your AMI in 6 months pulls a different vLLM and hits parser changes you didn't test. Always pin to a digest.
- **Marketplace listing claims Claude Code as a feature** (e.g., "Comes with Claude Code"). Reword to "Configures Claude Code (installed on first boot from Anthropic) for local model routing." The distinction matters.
- **Failure to test in a different VPC/account** before publishing. Tier 1 → Tier 2 jump must include this check; subtle networking issues (e.g., assuming a specific NAT setup) can break the firstboot install for users.
