# Troubleshooting and tuning

Deep dive on why the recipe in `01-setup-from-scratch.md` is shaped the way it is, plus how to debug when something goes wrong.

## Memory budget on a single A10G (23 GiB)

The card is the binding constraint on this whole setup. Every choice in the vLLM command is pushing back against the same ~23 GiB.

| Component | Cost |
|-----------|------|
| AWQ weights for Qwen3-Coder-30B-A3B | ~16 GiB |
| CUDA workspace, kernels, FlashAttention buffers | ~0.5–1 GiB |
| KV cache pool (allocated upfront based on `--max-model-len`) | rest |
| Headroom (target) | ~1–2 GiB |

**KV cache cost per token, roughly:**

| Setting | Bytes per token | 32k tokens | 65k tokens |
|---------|----------------|------------|------------|
| FP16 KV (default) | ~120 KiB | ~4 GiB | ~8 GiB |
| FP8 KV (`--kv-cache-dtype fp8`) | ~60 KiB | ~2 GiB | ~4 GiB |

**Why we landed on `--max-model-len 65536 --kv-cache-dtype fp8`:**

- Weights (16) + workspace (1) + FP8 KV at 64k (4) = ~21 GiB → ~2 GiB headroom. Comfortable.
- Weights (16) + workspace (1) + FP16 KV at 64k (8) = ~25 GiB → won't fit. vLLM refuses to start.
- Weights (16) + workspace (1) + FP16 KV at 32k (4) = ~21 GiB → also works, but only 32k context, more frequent `/clear` cycles.

**Quality cost of FP8 KV cache:** in the noise for coding tasks. Activations (which stay FP16) drive output quality far more than KV cache precision. Nobody benchmarks this regression because it isn't measurable in practice.

**Speed cost of FP8 KV cache:** very slightly *positive* on Ampere because it relieves memory bandwidth pressure during attention.

## The "Maximum concurrency" log line

The single most important line in vLLM startup output:

```
INFO ... Maximum concurrency for 65536 tokens per request: 1.20x
```

Read as "I can fit 1.2 simultaneous full-context requests." With `--max-num-seqs 1` (we're a single-user setup) anything `>= 1.0x` is fine. If you see:

| Line | What to do |
|------|-----------|
| `>= 1.0x` | ✅ Good, proceed |
| `0.6x` to `0.99x` | ⚠️ Drop `--max-model-len` to `49152` |
| Container exits with OOM | ❌ Drop `--max-model-len` to `49152` or `32768` |

Get this line at any time:

```bash
docker logs vllm-claude-code 2>&1 | grep -E 'Maximum concurrency|GPU KV cache size'
```

## Ongoing monitoring — three terminals

**Terminal 1 — GPU memory:**

```bash
nvidia-smi --query-gpu=memory.used,memory.free,memory.total,utilization.gpu --format=csv -l 2
```

`memory.free` is the diagnostic. Healthy idle: ~2 GiB free. Healthy peak under load: ≥1 GiB free. Below 0.5 GiB free during a request → tune down `--max-model-len`.

**Terminal 2 — vLLM cache + throughput:**

```bash
docker logs -f vllm-claude-code 2>&1 | grep -E 'KV cache usage|Prefix cache|generation throughput'
```

Two key numbers:

- `GPU KV cache usage: X%` — instantaneous KV pool fill. If sustained >85%, you're about to hit the wall.
- `Prefix cache hit rate: X%` — should be ~95%+ if the attribution-header fix is working. If it's bouncing around 5-30%, something is invalidating the prefix on every request.

Healthy log line:

```
Avg prompt throughput: 65.5 tokens/s, Avg generation throughput: 17.5 tokens/s,
Running: 0 reqs, Waiting: 0 reqs, GPU KV cache usage: 0.0%, Prefix cache hit rate: 95.9%
```

The `Running: 0 reqs` between bursts is normal — vLLM frees the per-request KV when no requests are in flight. The prefix cache (different from KV cache) survives, which is why hit rate stays high.

**Terminal 3 — Claude Code itself:**

```bash
~/local-llm-claude.sh
```

Inside Claude Code, `/context` periodically. With `CONTEXT_WINDOW_OVERRIDE=65536` set, the percentage is honest.

## The four env vars everyone gets wrong

These are the env vars whose absence or misconfiguration causes the most baffling failure modes.

### `CLAUDE_CODE_ATTRIBUTION_HEADER=0`

**Symptom if missing:** Every Claude Code turn takes 15–30 seconds even after the first. `Prefix cache hit rate` in vLLM logs bounces around 5–20% instead of pinning near 95%. Whole experience feels sluggish for no obvious reason.

**Why:** Claude Code injects a per-request hash into the system prompt. vLLM's prefix cache hashes the prompt to find cached prefills; a different prompt every time means the ~6-8k tokens of system prompt + tool schemas get re-prefilled on every turn.

**Fix:** Must be in `~/.claude/settings.json` under `env`. **`export CLAUDE_CODE_ATTRIBUTION_HEADER=0` does not work** — Claude Code doesn't read it from the launching shell for this particular variable.

### `CLAUDE_CODE_DISABLE_1M_CONTEXT=1` and `CONTEXT_WINDOW_OVERRIDE=65536`

**Symptom if missing:** `/context` shows `local-coder[1m] · 22.4k/1m tokens (2%)` — Claude Code believes you have a 1 million token context window because it inherited that assumption from Qwen3-Coder's HF model card. Real ceiling is whatever you set in vLLM (e.g. 65k). When usage hits the real ceiling, vLLM rejects with "context length exceeded" and Claude Code starts retrying 9 times because it thinks the 400 must be transient.

**Why:** Claude Code doesn't read `max_model_len` from vLLM's `/v1/models` response. It looks at the model name → HF card → reported max context. For an arbitrary model behind `ANTHROPIC_BASE_URL` it has no reliable way to know the truth.

**Fix:** Both env vars in `~/.claude/settings.json`. After this, `/context` shows `local-coder · 22.4k/65k tokens (34%)` — real numbers.

### `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=70`

**Symptom if missing:** `/compact` fails with "context length exceeded" right when you need it most. Reason: by default, autocompact fires at ~95% usage, but `/compact` itself needs to send the conversation in *and* generate a summary out — which doesn't fit if you're already at 95%. So `/compact` never works and you have to `/clear` and lose the session.

**Fix:** Setting it to 70 means autocompact fires at ~45k tokens (in a 65k window), leaving ~20k for the compact roundtrip. Confirmed working in practice.

### `--dangerously-skip-permissions`

**Symptom if missing on a disposable instance:** Every Bash command prompts "Allow this command? [y/n]" which makes agentic workflows painfully turn-based.

**Fix:** Add the flag to the launcher's exec line. Only do this on disposable instances; on real machines you absolutely want the prompts.

## Common failure modes and what to check

### "Did 0 searches in 37ms" when asking Claude Code to web-search

**Not** a vLLM issue. Claude Code's built-in `WebSearch` tool is a *server tool* hardwired to Anthropic's hosted infrastructure (uses Anthropic's Brave integration with encrypted result blocks). When pointed at a local backend, Claude Code dispatches the tool, vLLM has no idea what to do with the `web_search_20260209` tool type, the tool returns nothing, and you see "0 searches."

**Fix:** Add an MCP search server. Tavily is the easiest — generous free tier, drop-in npm package:

```bash
jq '. + {
  "mcpServers": ((.mcpServers // {}) + {
    "tavily": {
      "command": "npx",
      "args": ["-y", "tavily-mcp@latest"],
      "env": { "TAVILY_API_KEY": "tvly-YOUR-KEY-HERE" }
    }
  })
}' ~/.claude/settings.json > ~/.claude/settings.json.tmp \
&& mv ~/.claude/settings.json.tmp ~/.claude/settings.json
```

Restart Claude Code. The model now sees `web_search` as an MCP tool and calls it correctly through the same tool-call path that's already verified working.

Alternative: `/permissions deny WebSearch` to remove it from the model's tool list entirely if you don't need search.

### Tool calls show as JSON text, not as `Bash(...)` indicators

**Cause:** Wrong `--tool-call-parser` for the model. The model emits JSON in a format the parser doesn't recognize, so vLLM returns it as `content` instead of `tool_calls`.

**Diagnostic:** The curl test from `01-setup-from-scratch.md` Step 7. Look at `tool_calls` vs `content`.

**Fix:** Use `--tool-call-parser qwen3_coder` for Qwen3-Coder family. The vLLM docs' suggestion to use `hermes` for "Qwen2.5" is wrong for the *Coder* variants — see `03-experiments-and-lessons.md` Lesson 1 for the full story.

### vLLM container exits at startup with `CUDA out of memory`

**Cause:** Requested KV cache pool doesn't fit alongside model weights.

**Fix progression**, from least to most disruptive:

1. Add `--kv-cache-dtype fp8` if you don't already have it.
2. Drop `--max-model-len` from 65536 → 49152 → 32768.
3. Drop `--gpu-memory-utilization` from 0.92 → 0.90 (counterintuitive but sometimes helps when activations need more headroom).
4. Use a smaller model (e.g. AWQ of a 14B model).

### vLLM logs HTTP 200, but Claude Code never sees a response

Watch the request lifecycle:

```bash
docker logs -f vllm-claude-code 2>&1 | grep -E 'POST /v1|messages'
```

If you see `200 OK` but Claude Code is hanging, it's almost always streaming/SSE — Claude Code expects server-sent events back, vLLM is sending them, but something between is buffering. Check whether you've got an HTTP proxy in the way (some corporate setups). On a vanilla EC2 instance this shouldn't happen.

### `/compact` fails with "context length exceeded"

**Cause:** You waited too long. `/compact` itself needs context budget to send the conversation in.

**Fix in the moment:** `/clear` and start fresh.

**Fix going forward:** Set `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=70`. Run `/compact` proactively at ~70% usage instead of waiting for the warning.

### Claude Code retries 9 times before giving up

**Cause:** vLLM is returning a 400 (usually "context length exceeded"). Claude Code interprets it as transient and retries.

**Diagnostic:** Watch vLLM logs during the retries:

```bash
docker logs -f vllm-claude-code 2>&1 | grep -E 'VLLMValidationError|HTTP/1.1" 4'
```

You'll see the validation error repeated for each retry attempt.

**Fix in the moment:** `Esc` cancels the current model turn, including the retry loop. Saves you from the ~3 minutes of dead time waiting for attempts 1-10.

**Fix going forward:** Make the real ceiling visible to Claude Code (`CONTEXT_WINDOW_OVERRIDE`) so it autocompacts before hitting 4xx.

### Slow first response after `/clear` or session start

**Expected**, not a bug. Prefill throughput on Qwen3-Coder-30B-A3B AWQ on A10G is ~1500 tok/s. Claude Code's system prompt + tool schemas + any CLAUDE.md is 6-10k tokens, so ~5-10 seconds before the first generated token. Subsequent turns are fast because of prefix caching.

If first response is taking >30 seconds: prefix cache isn't working. Check `Prefix cache hit rate` and the `CLAUDE_CODE_ATTRIBUTION_HEADER` setting.

## Knobs you can turn

| Knob | When to turn it |
|------|----------------|
| `--max-model-len` | Up if memory allows, down if OOM. 32k is the floor for usable Claude Code. |
| `--kv-cache-dtype` | `fp8` is the right answer on A10G. No reason to use `auto` (FP16) unless something's broken. |
| `--gpu-memory-utilization` | Lower (0.88) if activations are getting squeezed. Higher (0.95) only with great care. |
| `--max-num-seqs` | Stay at 1 for single-user dev. Higher numbers steal KV budget for hypothetical concurrency you don't have. |
| `CLAUDE_CODE_MAX_OUTPUT_TOKENS` | Lower (1024) for fast iterative coding, higher (4096+) for verbose explanation tasks. |
| `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` | 70 is conservative. 80 if you trust your sessions to stay focused; 60 if you do lots of `Bash` with verbose output. |

## Seriously useful one-liners

**Real context window** (truth source):

```bash
curl -s http://127.0.0.1:8000/v1/models | jq -r '.data[0].max_model_len'
```

**Live KV usage one-liner** (cleaner than tailing logs):

```bash
docker logs -f vllm-claude-code 2>&1 \
  | grep --line-buffered 'KV cache usage' \
  | awk -F'[:,]' '{
      for(i=1;i<=NF;i++) {
        if($i ~ /Running/)        run=$i
        if($i ~ /KV cache usage/) kv=$i
        if($i ~ /Prefix cache/)   pfx=$i
        if($i ~ /generation/)     gen=$i
      }
      printf "%s |%s |%s |%s\n", run, kv, gen, pfx
    }'
```

**Quickly tail just the request lifecycle:**

```bash
docker logs -f vllm-claude-code 2>&1 | grep -E '"POST /v1|HTTP/1.1" [45]'
```

**Detect when context is filling up** (alarm-style):

```bash
docker logs -f vllm-claude-code 2>&1 \
  | grep --line-buffered 'KV cache usage' \
  | awk -F'usage: |%' '{ if ($2+0 > 70) print "⚠️  KV at " $2 "%" }'
```

## Reducing context bloat from Bash output

Long Bash outputs (yum install, npm install, large file reads) chew through context fast. Two things that help.

### Project-level CLAUDE.md

Drop a `CLAUDE.md` in your working directory. Claude Code reads it at session start and treats it as part of the system prompt:

```markdown
# Project guidelines

When running package installation or other commands with verbose output,
pipe through `tail -20` or redirect to /tmp/install.log and only read the
relevant lines. Keep tool output short to preserve context budget.

When reading large files, use offset and limit parameters rather than
reading the whole file at once.
```

100 tokens of guidance up front saves thousands later.

### Lower `CLAUDE_CODE_MAX_OUTPUT_TOKENS`

In your launcher script, `CLAUDE_CODE_MAX_OUTPUT_TOKENS=1024` caps each turn's output, which indirectly nudges the model toward shorter Bash commands and tighter responses.

## A note on the `--enforce-eager` escape hatch

If vLLM hangs at startup after `Loading safetensors checkpoint shards: 100%` for more than ~3 minutes, it's stuck in CUDA graph capture (vLLM precompiles common shapes for speed). On A10G this is occasionally slow.

Add `--enforce-eager` to skip CUDA graphs entirely:

```bash
vllm/vllm-openai:latest \
  --enforce-eager \
  ...
```

Cost: ~10-15% throughput. Benefit: startup completes immediately. Worth using only if you genuinely can't get past graph capture.
