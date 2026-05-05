# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Podman: Podman__Tags
# Tag keys/values and naming helper for podman. Extracted from Podman__AWS__Client
# to break the circular import: helpers import from here; AWS__Client imports helpers.
# ═══════════════════════════════════════════════════════════════════════════════

from sg_compute.platforms.ec2.helpers.Stack__Naming                            import Stack__Naming


TAG_PURPOSE_KEY    = 'sg:purpose'
TAG_PURPOSE_VALUE  = 'podman'
TAG_STACK_NAME_KEY = 'sg:stack-name'
TAG_ALLOWED_IP_KEY = 'sg:allowed-ip'
TAG_CREATOR_KEY    = 'sg:creator'
TAG_SECTION_KEY    = 'sg:section'
TAG_SECTION_VALUE  = 'podman'


PODMAN_NAMING = Stack__Naming(section_prefix='podman')
