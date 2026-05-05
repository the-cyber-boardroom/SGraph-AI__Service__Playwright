# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Schema__Image__Build__Request
# Inputs to Image__Build__Service.build(). Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute.image.collections.List__Schema__Image__Stage__Item                 import List__Schema__Image__Stage__Item


class Schema__Image__Build__Request(Type_Safe):
    image_folder         : str                                                      # Folder holding the dockerfile + requirements.txt — copied first
    image_tag            : str                                                      # Full tag passed to `docker build -t` (usually <ECR>:latest)
    stage_items          : List__Schema__Image__Stage__Item                         # Anything else to copy into the build context
    dockerfile_name      : str = 'dockerfile'                                       # Lowercase per existing convention
    requirements_name    : str = 'requirements.txt'
    build_context_prefix : str = 'sg_image_build_'                                 # tempdir prefix; visible in CI logs when troubleshooting
