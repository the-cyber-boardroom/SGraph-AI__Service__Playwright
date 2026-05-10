# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Section__VLLM
# Bash fragment that starts the vllm/vllm-openai Docker container with the
# verified flag set for tool-calling. Binds to 127.0.0.1:8000 (SSM-only; not
# exposed to the network). Blocks until /v1/models responds so subsequent
# sections can rely on vLLM being up.
#
# Critical flags (from the 2026-05-10 local-claude recipe):
#   --tool-call-parser  — must match the model family; wrong parser → calls
#                         land in content as text (verified dead end: hermes
#                         with Qwen2.5-Coder).
#   --kv-cache-dtype fp8 — mandatory for max-model-len 65536 on 23 GiB A10G;
#                         vLLM refuses to start with "Maximum concurrency: 0.6x"
#                         without it.
#   --max-num-seqs 1    — single user; higher value steals KV budget.
#   --ipc=host          — required for vLLM's shared-memory tensor passing.
#   --restart unless-stopped — survives spot stop/start; warms from HF cache
#                         in ~90s instead of redownloading 16 GiB.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

TEMPLATE = '''\
# ── vLLM container ────────────────────────────────────────────────────────────
echo '[sg-compute] starting vLLM container...'
mkdir -p /home/ssm-user/.cache/huggingface
chown -R ssm-user:ssm-user /home/ssm-user/.cache
docker rm -f vllm-claude-code 2>/dev/null || true
docker run -d \
  --name vllm-claude-code \
  --gpus all \
  --ipc=host \
  --restart unless-stopped \
  -v /home/ssm-user/.cache/huggingface:/root/.cache/huggingface \
  -p 127.0.0.1:8000:8000 \
  vllm/vllm-openai:latest \
  --model {model} \
  --served-model-name {served_model_name} \
  --host 0.0.0.0 \
  --port 8000 \
  --max-model-len {max_model_len} \
  --max-num-seqs 1 \
  --gpu-memory-utilization {gpu_memory_utilization} \
  --kv-cache-dtype {kv_cache_dtype} \
  --enable-auto-tool-choice \
  --tool-call-parser {tool_parser}
echo '[sg-compute] waiting for vLLM to come up (first run: ~5 min for model download)...'
until curl -sf http://127.0.0.1:8000/v1/models > /dev/null 2>&1; do
  sleep 10
  echo '[sg-compute]   ... vLLM still loading'
done
echo "[sg-compute] vLLM ready: $(curl -s http://127.0.0.1:8000/v1/models | jq -r '.data[0].id')"
'''


class Section__VLLM(Type_Safe):

    def render(self, model                 : str   = 'QuantTrio/Qwen3-Coder-30B-A3B-Instruct-AWQ',
                     served_model_name     : str   = 'local-coder'                               ,
                     tool_parser           : str   = 'qwen3_coder'                               ,
                     max_model_len         : int   = 65536                                        ,
                     kv_cache_dtype        : str   = 'fp8'                                        ,
                     gpu_memory_utilization: float = 0.92                                         ) -> str:
        return TEMPLATE.format(
            model                  = model                  ,
            served_model_name      = served_model_name      ,
            tool_parser            = tool_parser            ,
            max_model_len          = max_model_len          ,
            kv_cache_dtype         = kv_cache_dtype         ,
            gpu_memory_utilization = gpu_memory_utilization ,
        )
