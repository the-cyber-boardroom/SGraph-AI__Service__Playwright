# Local Claude Code on EC2 GPU — Working Setup

A reproducible recipe for running [Claude Code](https://claude.com/claude-code) against a local GPU-served LLM on AWS EC2, with full agentic tool execution working end-to-end. Plus stateful workflows via [sgit](https://github.com/SGraph-AI/SG-Send) vaults — encrypted memory that survives the ephemeral instance.

**Status:** Verified working on `g5.xlarge` (NVIDIA A10G, 23 GiB), Amazon Linux 2023, vLLM `latest`, Claude Code v2.1.138, on May 10, 2026.

## Why this exists

Pointing Claude Code at a local model via `ANTHROPIC_BASE_URL` is officially supported by vLLM, but the published docs leave out the failure modes that determine whether the setup actually *works* for agentic coding. The default-recommended model + parser pairing in the vLLM docs is broken for tool calling. Several Claude Code env vars have to be set or you get either a 90% performance regression or a context window display that lies by 30x. The `WebSearch` tool is hard-wired to Anthropic's hosted infrastructure and silently no-ops against a local backend. None of this is in the official quickstarts.

This doc set captures a configuration that is verified working, the experiments and dead ends that led there, a real end-to-end agentic workflow as proof of life, and the path to packaging the setup as a reusable AMI.

## Document index

| File | What it covers |
|------|----------------|
| [`01-setup-from-scratch.md`](./01-setup-from-scratch.md) | Full reproduction recipe: EC2 → Docker → NVIDIA toolkit → vLLM → Claude Code. Aim is "20 minutes from blank instance to working `Bash(pwd)`." |
| [`02-troubleshooting-and-tuning.md`](./02-troubleshooting-and-tuning.md) | Memory math (KV cache, FP8), context window sizing, env var reference, monitoring commands, common failure modes and their fixes. |
| [`03-experiments-and-lessons.md`](./03-experiments-and-lessons.md) | Everything we tried that didn't work, why each failed, and what the takeaway was. Includes the Qwen2.5-Coder + hermes parser dead end. |
| [`04-end-to-end-example-sgit.md`](./04-end-to-end-example-sgit.md) | A real agentic workflow: Claude Code driving the `sgit` vault tool through a venv, recovering from errors, and completing a cross-machine collaboration cycle. Proves tool calling actually works. |
| [`05-ami-publishing.md`](./05-ami-publishing.md) | Baking this stack into a reusable AWS AMI: bake checklist, first-boot install pattern for license-clean Claude Code distribution, marketplace listing notes, and what to scrub before snapshotting. |

## TL;DR — what works

| Component | Choice | Why |
|-----------|--------|-----|
| Instance | `g5.xlarge` spot (NVIDIA A10G, 23 GiB) | Cheapest GPU that fits a useful model |
| Model | `QuantTrio/Qwen3-Coder-30B-A3B-Instruct-AWQ` | MoE, ~16 GiB in AWQ, strong agentic tool use |
| vLLM parser | `--tool-call-parser qwen3_coder` | Correctly extracts structured tool calls |
| KV cache | `--kv-cache-dtype fp8 --max-model-len 65536` | Doubles usable context with no quality cost |
| Claude Code env | `CLAUDE_CODE_ATTRIBUTION_HEADER=0` | Restores prefix caching (~90% speedup) |
| Claude Code env | `CLAUDE_CODE_DISABLE_1M_CONTEXT=1`, `CONTEXT_WINDOW_OVERRIDE=65536` | Makes `/context` display the truth |
| Stateful storage | `sgit` encrypted vaults | Persistent memory across ephemeral instances |
| Session resilience | `tmux` | Survives SSM/SSH disconnects |

## TL;DR — what doesn't work

- `Qwen2.5-Coder` + `--tool-call-parser hermes` (the official vLLM recommendation) — model emits JSON in code blocks, parser expects `<tool_call>` tags, tool calls land in `content` instead of `tool_calls`. Verified upstream as a known bug.
- Claude Code's built-in `WebSearch` tool against any non-Anthropic backend — it's a server tool that depends on Anthropic's infrastructure. Use an MCP search server instead.
- Single A10G + GLM-4.7-Flash — KV cache requirements push past 24 GiB even with FP8 KV. Possible on `g6e.xlarge` (L40S, 48 GiB) or `g5.2xlarge` with sharding.
- Going to `--max-model-len 65536` without `--kv-cache-dtype fp8` — vLLM refuses to start, "Maximum concurrency: 0.6x".
- Setting `CLAUDE_CODE_ATTRIBUTION_HEADER=0` via `export` in the shell — has no effect. Must be in `~/.claude/settings.json` under `env`.

## Architecture (slimmed for headless-CLI use)

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
        └── tool-call-parser=qwen3_coder        (the critical bit)
```

Single container. No Open WebUI, no Docker network, no extra port forwards. Console-only via SSM. Encrypted state via sgit vaults that sync to a remote, so the machine stays disposable but your work doesn't.

## Hardware ballpark

| Item | Cost |
|------|------|
| `g5.xlarge` spot, us-east-1 | ~$0.30–0.50/hour |
| `g5.xlarge` on-demand | ~$1.00/hour |
| EBS storage (200 GiB gp3) | ~$16/month |
| Spot interruption frequency | ~weekly in us-east-1d during the test period |

For full-time use, on-demand is more predictable. For periodic dev sessions with tolerance for interruption, spot is the right call — the HF model cache survives stop/start on the EBS volume, so a replacement instance warms up in ~2 minutes instead of redownloading 16 GiB of weights.

## What this is good for, and what it isn't

✅ Single-user agentic CLI workflows (Claude Code, Codex CLI, similar) backed by a private 30B-class model on your own GPU.

✅ Stateful work via sgit vaults — encrypted, version-controlled storage that turns ephemeral instances into a durable workflow. This is the actual reason the setup is interesting; without persistent memory, you'd just have a slower Claude.

✅ Spot-friendly: EBS-backed cache means a reclaimed instance can be replaced and back to working in ~3 minutes.

❌ Not a multi-user dev environment. The vLLM is configured for `--max-num-seqs 1`.

❌ Not a hosted-API replacement at scale. ~17–25 tokens/sec on A10G is plenty for interactive coding but not for batch.

❌ Not a Sonnet replacement on speed-sensitive work. If you bill by your time, hosted Claude is faster.

## What's intentionally out of scope

- LiteLLM proxy. We tested and it works, but it's an extra hop that adds nothing now that vLLM has native Anthropic Messages support.
- Multi-GPU setups. The recipe assumes a single 24 GiB card and gets the most out of it.
- Open WebUI. Useful one-time as a sanity-check chat interface; not needed for the day-to-day Claude Code workflow. Removed from the slimmed setup.
- Production hosting (auth, multi-tenancy, observability beyond `/metrics`). This is a single-user dev box behind SSM.
- Other clients (Codex, Cursor, Cline). The same vLLM + parser fix applies but the env-var dance is Claude-Code-specific.

## Provenance

This document set was assembled from a working session on May 10, 2026, running on a `g5.xlarge` spot instance (`i-0f65bdb50b0f93551`, us-east-1d) that was reclaimed by AWS shortly after the setup was verified end-to-end. The recipe in `01-setup-from-scratch.md` is what we used on the replacement instance, then refined into the slimmed-down AMI-ready version captured in `05-ami-publishing.md`.
