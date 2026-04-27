# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — OpenSearch__AWS__Client
# Sole AWS boundary for the OpenSearch + Dashboards sub-package. Mirrors the
# Elastic__AWS__Client / Ec2__AWS__Client patterns. AWS-touching methods land
# in subsequent slices (Phase B step 5c+); this file establishes the namespace
# and binds OS_NAMING via the shared Stack__Naming class.
#
# Tag convention (mirrors elastic + ec2):
#   sg:purpose      : opensearch
#   sg:stack-name   : {stack_name}                 ← logical name lookup
#   sg:allowed-ip   : {caller_ip}                  ← records what /32 was set
#   sg:creator      : git email or $USER
#   sg:section      : os
#
# Plan reference:
#   team/comms/plans/v0.1.96__playwright-stack-split__04__sp-os__opensearch.md
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.aws.Stack__Naming                            import Stack__Naming


TAG_PURPOSE_KEY     = 'sg:purpose'
TAG_PURPOSE_VALUE   = 'opensearch'
TAG_STACK_NAME_KEY  = 'sg:stack-name'
TAG_ALLOWED_IP_KEY  = 'sg:allowed-ip'
TAG_CREATOR_KEY     = 'sg:creator'
TAG_SECTION_KEY     = 'sg:section'
TAG_SECTION_VALUE   = 'os'


OS_NAMING = Stack__Naming(section_prefix='opensearch')                              # AWS Name tag carries 'opensearch-' prefix; never doubled


class OpenSearch__AWS__Client(Type_Safe):                                           # Narrow boto3 boundary — class methods land in Phase B step 5c
    pass
