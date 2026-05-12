# local-claude — Claude Code CLI in a container, pointed at host Ollama

Laptop-local twin of `sg lc`. Runs Claude Code inside Docker on your Mac with
an Anthropic→Ollama translation proxy in front of it.

## Architecture

```
Claude Code (container) ──Anthropic /v1/messages──▶ LiteLLM (container) ──/api/chat──▶ host Ollama
```

Claude Code only speaks the Anthropic Messages API. Ollama's `/v1` is an
OpenAI-compat shim, not Anthropic-compat — pointing Claude Code directly at
Ollama returns 404 ("model may not exist"). LiteLLM bridges the two
protocols and lives on the compose network as the `litellm` service.

## Prereqs (on the host Mac)

1. Ollama running and listening on all interfaces (so the LiteLLM container can reach it):

   ```bash
   launchctl setenv OLLAMA_HOST 0.0.0.0:11434
   # then quit and relaunch Ollama.app
   ```

   (Plain `ollama serve` from a shell with `OLLAMA_HOST=0.0.0.0:11434` works too.)

2. Models pulled on the host (the container will NOT pull). The shipped
   `litellm.config.yaml` registers these:

   - `llama3.1:8b`
   - `gemma4:e4b`
   - `gemma4:31b`
   - `deepseek-r1:32b`
   - `qwen3:30b`

## Build

```bash
docker compose -f docker-compose.local-claude.yml build
```

## Run

```bash
docker compose -f docker-compose.local-claude.yml run --rm local-claude
```

The current working directory is mounted at `/workspace`, so Claude can read
and edit project files. The container starts `claude --dangerously-skip-permissions`
by default. The `litellm` sidecar is brought up first and gated on its
health check.

## Switching models

Inside Claude Code, use `/model <name>` with any of the names registered in
`litellm.config.yaml` — no config edits or restart required:

```
/model qwen3:30b
/model deepseek-r1:32b
```

To add a model, append a new `model_name` block to
`docker/local-claude/litellm.config.yaml` and recreate the sidecar
(`docker compose -f docker-compose.local-claude.yml up -d --force-recreate litellm`).

## Override env vars

```bash
OLLAMA_MODEL=qwen3:30b \
docker compose -f docker-compose.local-claude.yml run --rm local-claude
```

`OLLAMA_MODEL` is propagated into every Claude tier
(Opus/Sonnet/Haiku/SmallFast) by the launcher.

## Troubleshooting

The launcher prints two probes on startup:

1. LiteLLM sidecar health (`$ANTHROPIC_BASE_URL/health/liveliness`)
2. Host Ollama model catalogue (`http://host.docker.internal:11434/api/tags`)

If the Ollama probe warns, check:

- Ollama is running on the host
- It is bound to `0.0.0.0:11434`, not the default `127.0.0.1:11434` — run
  `launchctl setenv OLLAMA_HOST 0.0.0.0:11434` and restart Ollama.app
- macOS firewall is not blocking inbound 11434

If LiteLLM 4xx/5xx errors show up inside Claude Code, tail its logs:

```bash
docker compose -f docker-compose.local-claude.yml logs -f litellm
```
