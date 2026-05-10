# ═══════════════════════════════════════════════════════════════════════════════
# Ephemeral EC2 — Ollama__User_Data__Builder
# Composes Section__* fragments into a cloud-init bash script.
# Order: Base → Shutdown → GPU_Verify → Ollama → Agent_Tools → Claude_Launch → Sidecar
# Shutdown is registered SECOND (before any spec work) so a script failure
# in a later section cannot leave the instance running past max_hours.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute.platforms.ec2.user_data.Section__Agent_Tools   import Section__Agent_Tools
from sg_compute.platforms.ec2.user_data.Section__Base          import Section__Base
from sg_compute.platforms.ec2.user_data.Section__Claude_Launch import Section__Claude_Launch
from sg_compute.platforms.ec2.user_data.Section__GPU_Verify    import Section__GPU_Verify
from sg_compute.platforms.ec2.user_data.Section__Ollama        import Section__Ollama
from sg_compute.platforms.ec2.user_data.Section__Shutdown      import Section__Shutdown
from sg_compute.platforms.ec2.user_data.Section__Sidecar       import Section__Sidecar

FOOTER = '\necho "[sg-compute] ollama boot complete at $(date -u +%FT%TZ)"\n'


class Ollama__User_Data__Builder(Type_Safe):

    def render(self, stack_name      : str  ,
                     region          : str  ,
                     model_name      : str  = 'gpt-oss:20b',
                     gpu_required    : bool = True               ,
                     pull_on_boot    : bool = True               ,
                     max_hours       : int  = 1                  ,
                     with_claude     : bool = False              ,
                     expose_api      : bool = False              ,
                     registry        : str  = ''                 ,
                     api_key_name    : str  = 'X-API-Key'        ,
                     api_key_ssm_path: str  = ''                 ) -> str:
        shutdown = Section__Shutdown().render(max_hours=max_hours) if max_hours > 0 else ''
        parts = [
            Section__Base()         .render(stack_name=stack_name)                                        ,
            shutdown                                                                                       ,
            Section__GPU_Verify()   .render(gpu_required=gpu_required)                                    ,
            Section__Ollama()       .render(model_name=model_name, expose_api=expose_api,
                                            pull_on_boot=pull_on_boot)                                    ,
            Section__Agent_Tools()  .render()                                                             ,
            Section__Claude_Launch().render(model_name=model_name, with_claude=with_claude)               ,
            Section__Sidecar()      .render(registry=registry, api_key_name=api_key_name,
                                            api_key_ssm_path=api_key_ssm_path)                            ,
        ]
        parts.append(FOOTER)
        return '\n'.join(p for p in parts if p)
