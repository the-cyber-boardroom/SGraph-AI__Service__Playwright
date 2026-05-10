# ═══════════════════════════════════════════════════════════════════════════════
# Ephemeral EC2 — Local_Claude__User_Data__Builder
# Composes Section__* fragments into a cloud-init bash script.
# Order: Base → Shutdown → GPU_Verify → Docker → NVIDIA_Container_Toolkit
#      → SGit_Venv → Claude_Code__Firstboot → VLLM → Sidecar
#
# Shutdown is registered SECOND (position 2) so a script failure in a later
# section cannot leave the instance running past max_hours (L9 lesson from
# the 2026-05-10 debrief: auto-terminate timer must precede all failable work).
# Agent_Tools is intentionally omitted: it targets ec2-user + python3.13 and is
# not used by the local-claude stack.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute.platforms.ec2.user_data.Section__Base                     import Section__Base
from sg_compute.platforms.ec2.user_data.Section__Claude_Code__Firstboot   import Section__Claude_Code__Firstboot
from sg_compute.platforms.ec2.user_data.Section__Docker                   import Section__Docker
from sg_compute.platforms.ec2.user_data.Section__GPU_Verify               import Section__GPU_Verify
from sg_compute.platforms.ec2.user_data.Section__NVIDIA_Container_Toolkit import Section__NVIDIA_Container_Toolkit
from sg_compute.platforms.ec2.user_data.Section__SGit_Venv                import Section__SGit_Venv
from sg_compute.platforms.ec2.user_data.Section__Shutdown                 import Section__Shutdown
from sg_compute.platforms.ec2.user_data.Section__Sidecar                  import Section__Sidecar
from sg_compute.platforms.ec2.user_data.Section__VLLM                     import Section__VLLM

FOOTER = ('\ntouch /var/lib/sg-compute-boot-ok\n'
          'echo "[sg-compute] local-claude boot complete at $(date -u +%FT%TZ)"\n')


class Local_Claude__User_Data__Builder(Type_Safe):

    def render(self, stack_name           : str   ,
                     region               : str   ,
                     model                : str   = 'QuantTrio/Qwen3-Coder-30B-A3B-Instruct-AWQ',
                     served_model_name    : str   = 'local-coder'                               ,
                     tool_parser          : str   = 'qwen3_coder'                               ,
                     max_model_len        : int   = 65536                                        ,
                     kv_cache_dtype       : str   = 'fp8'                                        ,
                     gpu_memory_utilization: float = 0.92                                        ,
                     max_hours            : float = 1.0                                          ,
                     gpu_required         : bool  = True                                         ,
                     with_claude_code     : bool  = True                                         ,
                     with_sgit            : bool  = True                                         ,
                     registry             : str   = ''                                           ,
                     api_key_name         : str   = 'X-API-Key'                                  ,
                     api_key_ssm_path     : str   = ''                                           ) -> str:
        shutdown = Section__Shutdown().render(max_hours=max_hours) if max_hours > 0 else ''
        parts = [
            Section__Base()                     .render(stack_name=stack_name)                 ,
            shutdown                                                                            ,
            Section__GPU_Verify()               .render(gpu_required=gpu_required)             ,
            Section__Docker()                   .render()                                      ,
            Section__NVIDIA_Container_Toolkit() .render()                                      ,
            Section__SGit_Venv()                .render() if with_sgit else ''                 ,
            Section__Claude_Code__Firstboot()   .render(served_model_name=served_model_name    ,
                                                        max_model_len=max_model_len)            if with_claude_code else '' ,
            Section__VLLM()                     .render(model=model                            ,
                                                        served_model_name=served_model_name    ,
                                                        tool_parser=tool_parser                ,
                                                        max_model_len=max_model_len            ,
                                                        kv_cache_dtype=kv_cache_dtype          ,
                                                        gpu_memory_utilization=gpu_memory_utilization) ,
            Section__Sidecar()                  .render(registry=registry                       ,
                                                        api_key_name=api_key_name              ,
                                                        api_key_ssm_path=api_key_ssm_path)     ,
        ]
        parts.append(FOOTER)
        return '\n'.join(p for p in parts if p)
