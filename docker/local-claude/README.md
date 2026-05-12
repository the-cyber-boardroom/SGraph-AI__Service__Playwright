# local-claude — Claude Code CLI in a container, pointed at host Ollama

Laptop-local twin of `sg lc`. Runs Claude Code inside Docker on your Mac, with
`ANTHROPIC_BASE_URL` pointed at the host's Ollama OpenAI-compat endpoint.

## Prereqs (on the host Mac)

1. Ollama running and listening on all interfaces (so the container can reach it):

   ```bash
   OLLAMA_HOST=0.0.0.0:11434 ollama serve
   ```

2. Your target model already pulled on the host (the container will NOT pull):

   ```bash
   ollama pull llama3.1:8b
   ```

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
by default.

## Override env vars

```bash
OLLAMA_MODEL=qwen2.5-coder:14b \
ANTHROPIC_BASE_URL=http://host.docker.internal:11434/v1 \
docker compose -f docker-compose.local-claude.yml run --rm local-claude
```

`OLLAMA_MODEL` is propagated into every Claude tier
(Opus/Sonnet/Haiku/SmallFast) by the launcher.

## Troubleshooting

The launcher prints the host Ollama model list on startup. If you see
`WARNING: could not reach …/api/tags`, check:

- `ollama serve` is running on the host
- It is bound to `0.0.0.0:11434`, not the default `127.0.0.1:11434`
- macOS firewall is not blocking inbound 11434
