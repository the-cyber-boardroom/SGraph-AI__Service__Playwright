# Experiments and lessons learned

The recipe in `01-setup-from-scratch.md` looks simple in hindsight, but it took several false starts to find. This doc captures the experiments that didn't work and what each one taught us. Useful for future-you when you wonder "why exactly are we using *this* model with *this* parser?"

---

## Lesson 1 — The vLLM docs lie about Qwen2.5-Coder

**What we tried first:** the configuration the official vLLM Claude Code integration page suggests for Qwen-family models.

```bash
--model Qwen/Qwen2.5-Coder-7B-Instruct
--tool-call-parser hermes
--enable-auto-tool-choice
```

**What happened:**

Basic chat worked. `/v1/chat/completions` worked. `/v1/messages?beta=true` returned 200 OK. Claude Code launched, basic prompts worked. But every time the model tried to use a tool, it emitted JSON as plain assistant text:

```
● I'll use the Bash tool to run pwd:
  {
    "name": "Bash",
    "arguments": {
      "command": "pwd"
    }
  }
```

No `Bash(pwd)` indicator, no tool dispatch, no command output. Just text that looked like a tool call.

**Root cause:**

The vLLM docs say "use `hermes` for Qwen2.5 models." That's correct for `Qwen/Qwen2.5-7B-Instruct` (the base instruct model), which was trained on Hermes-style `<tool_call>` token format. **It is wrong for Qwen2.5-*Coder*** — the Coder variant was not trained on those tokens. Instead, it emits tool calls as JSON in markdown code blocks (```` ```json ... ``` ````), or sometimes inside `<tools>` tags. The hermes parser looks for `<tool_call>...</tool_call>`, doesn't find it, so all the JSON ends up in the response's `content` field with `tool_calls` empty.

**Verified upstream as a known bug:**

- vLLM #10952 (Dec 2024) — "Function calling not working properly for Qwen2.5-Coder models"
- vLLM #29192 (Nov 2025) — "Tool Calling Parsers Fail to Populate tool_calls Array for Qwen2.5-Coder Models"
- vLLM #32926 (Jan 2026) — proposes adding a dedicated `qwen2_5_coder` parser

**What actually fixed it:**

Switching to `Qwen3-Coder-30B-A3B-Instruct` with `--tool-call-parser qwen3_coder`. The Qwen3-Coder family was trained explicitly for agentic tool use with a parser that ships in vLLM upstream. After the switch, the curl test returns a populated `tool_calls` array immediately.

**Takeaway:** Never assume the parser works just because the docs say it should. The 60-second curl test from `01-setup-from-scratch.md` Step 7 is the only way to be sure. Run it before launching Claude Code, every time you change the model or parser.

---

## Lesson 2 — Context size affects everything, including whether Claude Code is usable

**What we tried:** Default vLLM context (`--max-model-len 8192`).

**What happened:** Claude Code's own system prompt (~5.5k tokens) plus tool schemas (~15.8k tokens) is already ~21k tokens — three times the budget. vLLM rejected requests with "context length exceeded" before the model even saw anything. Bumped to 16384, still couldn't fit a single tool-using request. Bumped to 32768, finally workable.

**Key data point from vLLM logs (32k config, real session):**

```
GPU KV cache usage: 60.4%
```

That's during a mid-session conversation. 60% of 32k = ~20k tokens loaded — and that's already most of Claude Code's static overhead. You have ~13k tokens of effective working room before hitting the wall.

**Takeaway:** The Claude Code integration is essentially unusable below `--max-model-len 32768`. Treat 32k as the absolute floor; 64k is more comfortable.

---

## Lesson 3 — FP8 KV cache is free real estate on Ampere

**What we tried:** Pushing from 32k to 64k context without changing KV cache precision.

**What happened:** vLLM refused to start with `Maximum concurrency for 65536 tokens per request: 0.62x` and a "won't be able to serve a single request" warning. Reason: 64k of FP16 KV cache is ~8 GiB; combined with 16 GiB of weights and ~1 GiB of workspace, you're past 25 GiB on a 23 GiB card.

**What worked:** Adding `--kv-cache-dtype fp8`. KV cache memory cost halved per token, so 64k now fits in ~4 GiB of cache. vLLM started cleanly with `Maximum concurrency: 1.20x`.

**Quality / speed cost:** Imperceptible. KV cache precision affects attention's "look-back" quality at very long contexts; for coding tasks this is in the noise. Throughput was actually slightly *better* with FP8 KV because of reduced memory bandwidth pressure.

**Takeaway:** On Ampere/A10G with a 30B-class AWQ MoE, `--kv-cache-dtype fp8` is the obvious default. There's no reason to leave it off.

---

## Lesson 4 — `export` doesn't work for some Claude Code env vars

**What we tried:** `export CLAUDE_CODE_ATTRIBUTION_HEADER=0` in the launcher script (the obvious thing).

**What happened:** No effect. Prefix cache hit rate stayed pinned at 5-20%, every Claude Code turn took 15+ seconds even for trivial prompts.

**Root cause:** Claude Code reads certain env vars from `~/.claude/settings.json` at startup (under the `env` key), not from the launching shell's environment. `CLAUDE_CODE_ATTRIBUTION_HEADER`, `CONTEXT_WINDOW_OVERRIDE`, and `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` are in this category. `ANTHROPIC_BASE_URL` and `ANTHROPIC_MODEL` work fine via export — the rule isn't uniform.

**Verified by Anthropic** in the documented `env` section of `settings.json` and in [community guides](https://unsloth.ai/docs/basics/claude-code) ("Using `export CLAUDE_CODE_ATTRIBUTION_HEADER=0` does NOT work").

**What actually worked:**

```json
{
  "env": {
    "CLAUDE_CODE_ATTRIBUTION_HEADER": "0"
  }
}
```

After this, prefix cache hit rate jumped to 96% and stayed there. Subsequent turns went from 15 seconds to ~2 seconds.

**Takeaway:** When in doubt, put env vars in `~/.claude/settings.json` under `env`. Belt and suspenders never hurts.

---

## Lesson 5 — Claude Code lies about your context window

**What we tried:** Trusting `/context`'s display of `local-coder[1m] · 22.4k/1m tokens (2%)`.

**What happened:** vLLM rejected a request with "context length exceeded: 30721 input tokens > 32768 max." Claude Code interpreted the 400 as transient and started retrying with exponential backoff. By attempt 9 of 10, after several minutes of dead time, we noticed something was off.

**Root cause:** Claude Code reads the model's context window from the HF model card (Qwen3-Coder advertises 1M with YaRN scaling), not from vLLM's `/v1/models` response (which correctly reports 32768 or 65536 depending on the `--max-model-len` flag). Result: Claude Code thinks it has 30x more headroom than it actually does, and behaves accordingly — including not autocompacting until far past the real wall.

**What actually worked:** Two env vars in `~/.claude/settings.json`:

```json
{
  "env": {
    "CLAUDE_CODE_DISABLE_1M_CONTEXT": "1",
    "CONTEXT_WINDOW_OVERRIDE": "65536"
  }
}
```

After this, `/context` shows `local-coder · 22.4k/65k tokens (34%)` — real numbers, real percentages, real autocompact triggers.

**Takeaway:** With `ANTHROPIC_BASE_URL` setups, **always** override the context window. The default is wildly wrong and the failure mode is silent.

---

## Lesson 6 — `WebSearch` is hard-wired to Anthropic's hosted backend

**What we tried:** Asking Claude Code to web-search for Python install instructions.

**What happened:**

```
● Web Search("install python 3.13 Amazon Linux 2023")
  ⎿  Did 0 searches in 13ms
```

The model correctly emitted a structured tool call (verified via vLLM logs — tool calling is genuinely working). The dispatch took 13ms, returned nothing, and Claude Code printed the "0 searches" message.

**Root cause:** Claude Code's built-in `WebSearch` is a *server tool* — `web_search_20260209`. It's executed inside Anthropic's API, not by Claude Code locally. When Claude Code points at vLLM, vLLM has no idea what to do with the `web_search_20260209` tool type. There's [an open Claude Code issue](https://github.com/anthropics/claude-code/issues/10141) tracking this.

You can't just hand Claude Code a Brave/Tavily API key — its `WebSearch` tool isn't designed to be configurable.

**What actually works:** MCP search server. Tavily was the easiest option (free tier, npm package, MCP-compatible):

```json
{
  "mcpServers": {
    "tavily": {
      "command": "npx",
      "args": ["-y", "tavily-mcp@latest"],
      "env": { "TAVILY_API_KEY": "tvly-..." }
    }
  }
}
```

The model then sees `web_search` as a regular MCP tool, calls it through the same path as `Bash` and `Read`, and gets real results. This works because we already proved the tool-call path is solid; MCP just adds another tool to the list.

**Takeaway:** Local Claude Code = no `WebSearch`. Add an MCP search server, or `/permissions deny WebSearch` to remove the broken tool from the model's view entirely.

---

## Lesson 7 — Spot interruptions are recoverable if you persist the EBS volume

**What happened:** During the working session, AWS reclaimed the spot instance.

**Setup choices that helped:**

- "Stop, don't terminate" on spot interruption → EBS volume survives.
- HF cache mounted at `~/.cache/huggingface` on the EBS volume → 16 GiB of model weights survive.
- `--restart unless-stopped` on the vLLM container → comes back automatically when Docker starts.
- Reproducible launcher script (`~/bin/start-vllm.sh`) → if Docker doesn't auto-restart, one command brings everything back.

**Time to recovery on a replacement instance:** ~3 minutes (vs ~15 minutes from a blank instance, mostly model download).

**Takeaway:** For any setup involving multi-GiB model downloads, treat the EBS volume as the durable thing and the instance as ephemeral. Put as much as possible on the volume, including HF cache and Docker images. The only reason a replacement instance should redownload anything is if you change the model.

---

## Lesson 8 — `/compact` doesn't work if you wait too long

**What we tried:** Hitting `/compact` after vLLM started rejecting requests.

**What happened:** `/compact` failed with the same "context length exceeded" error.

**Root cause:** `/compact` itself sends the entire conversation to the model and asks for a summary back. If you're already past the context limit, the compact request also doesn't fit. Catch-22.

**Fix:** `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=70` in `~/.claude/settings.json`. Autocompact fires at 70% of real context window (~45k of 64k), leaving plenty of room for the compact roundtrip itself.

**Takeaway:** Don't wait for the wall to compact. Compact proactively. The env var change makes Claude Code do this for you.

---

## Lesson 9 — Some things are just irreducibly slow on a 24 GiB card

**Observed metrics on the working setup:**

| Metric | Value |
|--------|-------|
| Prompt throughput (prefill) | ~1500 tokens/s |
| Generation throughput (steady state) | ~17-25 tokens/s |
| First response after `/clear` | ~5-10 seconds |
| Subsequent turns (cached prefix) | ~2-5 seconds |
| Cold model load (download) | ~2 minutes |
| Cold model load (cached) | ~60-90 seconds |

**Comparison:**

- Anthropic-hosted Sonnet: ~50-150 tokens/s generation. Prefill effectively instant from user's POV.
- This local setup: ~17-25 tokens/s generation. Noticeable lag on long responses.

**What this means in practice:** Single-question chat is fine. Long agentic loops with many tool calls feel slower than hosted Claude. For very large codebase work, this hardware is the bottleneck, not the model.

**Takeaway:** This setup is great for "I want a private, free, agentic coding assistant for personal projects." It's not a Sonnet replacement for production work. If raw speed matters more than privacy/cost, hosted is better. If neither, this is a sweet spot.

---

---

## Lesson 10 — Removing components is harder than adding them

Our first working setup had vLLM + Open WebUI + a Docker network connecting them, with SSM port forwards for both. Open WebUI was useful exactly once: as a sanity-check chat interface to confirm the model was alive and responsive before debugging Claude Code. After that it sat idle for the entire session.

When we slimmed for the AMI, removing Open WebUI saved:
- One Docker container (~250 MB image, ~100 MB RAM)
- One Docker network (`llm-net`)
- One SSM port forward (`:8080` → `:3000`)
- Two env vars passed to the container
- ~10 lines from the setup recipe

None of this was big individually. Together it's the difference between a setup people *use* and one they tolerate. **Anything that's not on the critical path for the headline workflow should be optional, in a "nice to have" appendix or a separate doc.** If you find yourself documenting something with "you don't need this but...", that's a signal to remove it from the main flow.

The slimmed AMI build (see `05-ami-publishing.md`) goes further — single container, single Python venv, three scripts, and a login MOTD. Less to misconfigure, less to debug, less to maintain.

---

## Things we considered but didn't pursue

### GLM-4.7-Flash on a single A10G

[Z.AI's GLM-4.7-Flash](https://huggingface.co/zai-org/GLM-4.7-Flash) is reported to work well with Claude Code. It also has a working `glm47` parser in vLLM. But:

- Default precision pushes past 24 GiB before context. Needs FP8 weights (`unsloth/GLM-4.7-Flash-FP8-Dynamic`) and aggressive KV trimming to fit.
- HF discussion threads show people getting "120 GiB KV cache needed" errors at full 131k context. Even at trimmed 32k, on a single A10G, it's borderline.
- Realistic deployment is `g6e.xlarge` (L40S, 48 GiB) or 2x A10G with tensor parallelism.

We stuck with Qwen3-Coder-30B-A3B as the pragmatic choice for a single 24 GiB GPU. Revisit GLM if you upgrade hardware.

### Custom community parser for Qwen2.5-Coder

The `hanXen/vllm-qwen2.5-coder-tool-parser` plugin is a working third-party parser for the model. We could have stayed on Qwen2.5-Coder and added the plugin via `--tool-parser-plugin`. Decided against because:

- Qwen3-Coder is genuinely better at agentic tool use than Qwen2.5-Coder (purpose-built for it).
- Maintaining a third-party parser plugin is friction vs. a standard upstream parser.
- Switching the model is one CLI flag; switching to a plugin requires extra setup.

If you're stuck on Qwen2.5-Coder for some reason (existing fine-tuning, comparison studies), the plugin is the right answer.

### LiteLLM proxy

Some guides recommend a LiteLLM proxy between Claude Code and vLLM to handle Anthropic-format ↔ OpenAI-format translation. This was the right answer in 2025 before vLLM had native `/v1/messages` support. As of vLLM `latest` (May 2026), it's redundant — vLLM speaks the Anthropic Messages API directly. Adds an extra hop, extra latency, extra failure mode. Skip it.

### Claude Code router (musistudio/claude-code-router)

A popular alternative to LiteLLM with similar role. Same reasoning — not needed now that vLLM is native. Useful only if you want to route across multiple backends.

---

## Things that would change with bigger hardware

| If you have | Change |
|-------------|--------|
| 2x A10G | `--tensor-parallel-size 2`, larger model (e.g. GLM-4.7-Flash, Qwen3-Coder-30B at higher precision), 128k context easily |
| L40S 48 GiB single card | GLM-4.7-Flash fits comfortably with FP8. Drop AWQ, use BF16 weights. |
| H100 80 GiB | Qwen3-Coder-30B at full BF16, `--enable-prefix-caching`, `--enable-chunked-prefill`, full 256k context, MTP for ~2x speedup |
| Multiple H100s | Stop reading this doc and use the proper deployment guides |

The recipe in this doc set is the *minimum viable* setup that gives you a working agentic Claude Code. Everything else is optimization.
