# 2026-05-12 — local-claude Mac container (laptop twin of `sg lc`)

**Branch:** `claude/ollama-mac-container-14CDT`
**Commits:** `1e692ce` (initial), `41a4bd1` (UID fix), `34a6a49` (LiteLLM sidecar),
`0af2990` (gemma4:e2b), `fd7ace0` (qwen2.5-coder:7b default), plus this debrief
**Scope:** new feature, additive only — zero changes to `sg lc` / EC2 path.

═══════════════════════════════════════════════════════════════════════════════
## Goal
═══════════════════════════════════════════════════════════════════════════════

Replicate the **`sg lc` (EC2 local-claude)** developer experience on a 24 GB
Apple M5 Mac. Same idea: run Claude Code CLI inside an isolated container
that talks to a local LLM. The EC2 path uses vLLM serving
`QuantTrio/Qwen3-Coder-30B-A3B-Instruct-AWQ` on an A10G; the Mac path uses
Ollama on the host (only way to get Metal/GPU acceleration as of 2026-05)
with a containerised Claude Code on top.

═══════════════════════════════════════════════════════════════════════════════
## What landed
═══════════════════════════════════════════════════════════════════════════════

All files under `docker/local-claude/`:

| File                          | Role |
|------------------------------|------|
| `Dockerfile`                  | `node:22-bookworm-slim` + git/curl/jq/python3/ripgrep/tini + `@anthropic-ai/claude-code` global install; non-root `claude` user (UID 1000); `/workspace` mount point |
| `local-llm-claude.sh`         | Mirror of EC2 launcher at `sg_compute/platforms/ec2/user_data/Section__Claude_Code__Firstboot.py:74-97`. Exports `ANTHROPIC_BASE_URL`, dummy `ANTHROPIC_API_KEY`, and propagates `OLLAMA_MODEL` into every Claude tier. Two warn-only pre-flight probes (LiteLLM `/health/liveliness`, host Ollama `/api/tags`) |
| `settings.json`               | `~/.claude/settings.json` template — env block with `ANTHROPIC_BASE_URL`, `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` |
| `litellm.config.yaml`         | Anthropic→Ollama translation map. 7 host models registered. `drop_params: true` to tolerate Anthropic-only params LiteLLM can't forward |
| `docker-compose.yml`          | Two-service stack: `litellm` (Anthropic-compat proxy) + `local-claude` (CLI). `local-claude` `depends_on: { litellm: service_healthy }`. Workspace mount `../../:/workspace` (compose resolves relative to this file → repo root) |
| `README.md`                   | Usage, prereqs, troubleshooting, model-switching via `/model` |

Default model: **`qwen2.5-coder:7b`** (≈5 GB, strong tool-calling, fast on M5).

═══════════════════════════════════════════════════════════════════════════════
## Architecture
═══════════════════════════════════════════════════════════════════════════════

```
┌────────────────────── macOS host (M5, 24 GB) ──────────────────────┐
│                                                                     │
│  ollama serve  ──  OLLAMA_HOST=0.0.0.0:11434                        │
│                            ▲                                         │
│                            │ /api/chat                               │
│  ┌─────────── Docker Desktop ─────────────────────────────┐         │
│  │                       │                                │         │
│  │   ┌──────────────┐    │     ┌────────────────────┐    │         │
│  │   │  litellm     │────┘     │  local-claude      │    │         │
│  │   │  :4000       │◀─────────│  (Claude Code CLI) │    │         │
│  │   │              │  /v1/    │                    │    │         │
│  │   │  Anthropic   │ messages │  /workspace = repo │    │         │
│  │   │  compat      │          │                    │    │         │
│  │   └──────────────┘          └────────────────────┘    │         │
│  └──────────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────────┘
```

The model-machine is the host. Ollama uses Metal directly. Containers reach
the host via `host.docker.internal` (resolved natively on Docker Desktop;
`extra_hosts: ["host.docker.internal:host-gateway"]` is kept for non-DD
runtimes).

═══════════════════════════════════════════════════════════════════════════════
## Challenges hit (in order)
═══════════════════════════════════════════════════════════════════════════════

### 1. UID 1000 collision — `useradd … --uid 1000 claude` failed

**Symptom:** `useradd: UID 1000 is not unique` during image build.

**Root cause:** The `node:22-bookworm-slim` base image ships with a `node`
user already at UID 1000.

**Fix:** `userdel -r node 2>/dev/null || true` before `useradd …`.
Commit `41a4bd1`.

**Classification: BAD failure** — should have been caught in the initial
Dockerfile. Cheap lesson: when claiming a UID on a chosen base, check
`/etc/passwd` for collisions first.

---

### 2. Ollama bound to loopback only — container couldn't reach host

**Symptom:** `curl -s http://host.docker.internal:11434/api/tags` from inside
the container returned **empty body, no error** (because `-s` suppresses).
With `-v`: connection refused.

**Root cause:** Ollama defaults to `127.0.0.1:11434`. From the container,
`host.docker.internal` resolves to the host's *external* interface, not
loopback, so the bind is unreachable.

**Fix on host:**
```bash
launchctl setenv OLLAMA_HOST 0.0.0.0:11434
# then fully quit and relaunch Ollama.app
```
Plus `lsof -iTCP:11434 -sTCP:LISTEN` to verify `*:11434`.

**Classification: GOOD failure** — surfaced fast, documented in README,
matches the precedent already in `sg_compute/platforms/ec2/user_data/Section__Ollama.py:9-16`
which does the same `OLLAMA_HOST=0.0.0.0:11434` rebind via systemd drop-in on
the EC2 path.

---

### 3. Anthropic vs OpenAI API mismatch — "model may not exist"

**Symptom:** Claude Code v2.1.139 launched cleanly, models were visible from
the pre-flight probe, but every prompt returned:
> *There's an issue with the selected model (llama3.1:8b). It may not exist
> or you may not have access to it.*

**Root cause:** Claude Code speaks the **Anthropic Messages API**
(`POST /v1/messages`). Ollama's `/v1` is an **OpenAI-compatible shim**
(`POST /v1/chat/completions`). Different wire format. Ollama 404s the
Anthropic POST → Claude Code surfaces a generic "model may not exist" error.
The EC2 `sg lc` path doesn't hit this because vLLM there is configured with
a tool-parser that exposes an Anthropic-compatible surface; Ollama is not.

**Fix:** Inserted **LiteLLM** as a sidecar proxy:
- Listens on `:4000` inside the compose network
- Exposes `/v1/messages` (Anthropic-compat)
- Forwards to `ollama_chat/<model>` (Ollama native `/api/chat`, more reliable
  than the `ollama/` OpenAI shim for tool use)
- `drop_params: true` to silently drop Anthropic-only fields LiteLLM can't map

Commit `34a6a49`.

**Classification: GOOD failure** — clear symptom, clean root cause, fix
matches industry-standard pattern. The cost: we now have a proxy in the loop,
which means tool-use quality is bounded by LiteLLM's translation fidelity
AND the underlying Ollama model's tool-calling ability. Worth it.

---

### 4. Model selection on 24 GB unified memory

**Symptom:** User's `ollama list` showed 9.6 GB / 18 / 19 / 19 GB models —
dense 30 B+ models would swap on a 24 GB Mac with macOS + Docker + browser
already resident.

**Resolution:**
- Recommended: delete `deepseek-r1:32b` (reasoning model, weak tool-calling)
  and `gemma4:31b` (dense 31 B, swaps).
- Default model promoted to `qwen2.5-coder:7b` (~5 GB, strong tool use,
  same family as the EC2 `sg lc` default `QuantTrio/Qwen3-Coder-30B-A3B-Instruct-AWQ`).
- `qwen3:30b` kept as the heavyweight option — it's MoE (~3 B active) so
  fast despite the on-disk size.

Commit `fd7ace0`.

**Classification: GOOD failure** — caught before the user wasted time on
swap-thrashing models.

═══════════════════════════════════════════════════════════════════════════════
## Non-failures worth recording
═══════════════════════════════════════════════════════════════════════════════

- **Compose volume paths are resolved relative to the compose file**, not the
  shell's cwd. Moving `docker-compose.yml` into `docker/local-claude/`
  required changing `./:/workspace` → `../../:/workspace` and
  `./docker/local-claude/litellm.config.yaml` → `./litellm.config.yaml`.
  Verified by reading Compose docs, not by trial.
- **`ANTHROPIC_BASE_URL` does not include `/v1`** — the Anthropic SDK
  appends `/v1/messages` itself. Standard convention; LiteLLM serves
  `/v1/messages` at the root, so `http://litellm:4000` is correct.
- **Apple `container` CLI was explicitly skipped** at user's request — Docker
  Desktop only. Less surface area, less to verify.

═══════════════════════════════════════════════════════════════════════════════
## How to use
═══════════════════════════════════════════════════════════════════════════════

```bash
# one-time host setup
launchctl setenv OLLAMA_HOST 0.0.0.0:11434          # then restart Ollama.app
ollama pull qwen2.5-coder:7b                         # default model

# build + run
docker compose -f docker/local-claude/docker-compose.yml build
docker compose -f docker/local-claude/docker-compose.yml run --rm local-claude

# switch model inside Claude Code
/model qwen3:30b
```

═══════════════════════════════════════════════════════════════════════════════
## Open follow-ups
═══════════════════════════════════════════════════════════════════════════════

1. **Tool-use quality varies by model.** `qwen2.5-coder:7b` and `qwen3:30b`
   tool-call reliably; gemma4 small variants and `llama3.1:8b` are hit-or-miss;
   `deepseek-r1:32b` emits `<think>` traces and rarely tool-calls cleanly.
   A "best model for Claude-Code-style agent loops on Mac" guidance note
   could live under `library/guides/` if/when the user stabilises a workflow.
2. **LiteLLM image tag is `main-stable`** — fine for local dev, should pin
   to a dated tag for reproducibility once we have a known-good one.
3. **"Our own version of Claude chat"** — user expressed interest in writing
   a thin agent that talks to Ollama directly (no Anthropic translation, no
   Claude Code overhead). Scoping sketch was drafted in transcript but no
   code written. Likely a separate branch / future debrief.
4. **Reality doc not updated** — this slice is dev-tooling, not a service
   feature. If the Librarian wants to record it, the entry would go under a
   "developer tooling" subsection of the current reality doc, noting that
   nothing in `sgraph_ai_service_playwright/` source changed.

═══════════════════════════════════════════════════════════════════════════════
## Files cross-reference
═══════════════════════════════════════════════════════════════════════════════

| Path | Purpose |
|------|---------|
| `docker/local-claude/Dockerfile`              | image build |
| `docker/local-claude/docker-compose.yml`      | two-service stack |
| `docker/local-claude/local-llm-claude.sh`     | container entrypoint / launcher |
| `docker/local-claude/settings.json`           | bundled `~/.claude/settings.json` |
| `docker/local-claude/litellm.config.yaml`     | model registry + Anthropic→Ollama routing |
| `docker/local-claude/README.md`               | usage docs |
| `sg_compute/platforms/ec2/user_data/Section__Claude_Code__Firstboot.py` | EC2 precedent — launcher pattern mirrored |
| `sg_compute/platforms/ec2/user_data/Section__Ollama.py`                 | EC2 precedent — `OLLAMA_HOST=0.0.0.0:11434` rebind |
| `library/guides/v0.1.23__local_proxy_auth_validation.md`                | repo precedent for `host.docker.internal:host-gateway` |
