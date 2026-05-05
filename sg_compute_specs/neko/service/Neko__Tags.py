# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Neko: Neko__Tags
# Tag keys/values and naming helper for neko. Extracted from Neko__AWS__Client
# to break the circular import: helpers import from here; AWS__Client imports helpers.
# ═══════════════════════════════════════════════════════════════════════════════

from sg_compute.platforms.ec2.helpers.Stack__Naming                            import Stack__Naming


TAG_PURPOSE_KEY    = 'sg:purpose'
TAG_PURPOSE_VALUE  = 'neko'
TAG_STACK_NAME_KEY = 'sg:stack-name'
TAG_ALLOWED_IP_KEY = 'sg:allowed-ip'
TAG_CREATOR_KEY    = 'sg:creator'
TAG_SECTION_KEY    = 'sg:section'
TAG_SECTION_VALUE  = 'neko'


NEKO_NAMING = Stack__Naming(section_prefix='neko')
