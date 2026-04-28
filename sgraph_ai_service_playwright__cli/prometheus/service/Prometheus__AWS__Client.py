# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Prometheus__AWS__Client
# Composition shell for the per-concern AWS helpers (SG / Instance / Tags /
# Launch). Mirrors the OpenSearch__AWS__Client + Elastic__AWS__Client +
# Ec2__AWS__Client patterns. Owns the tag-key constants and the PROM_NAMING
# binding so the section's AWS surface is in one shared header.
#
# Tag convention (mirrors elastic + os + ec2):
#   sg:purpose      : prometheus
#   sg:stack-name   : {stack_name}                 ← logical name lookup
#   sg:allowed-ip   : {caller_ip}                  ← records what /32 was set
#   sg:creator      : git email or $USER
#   sg:section      : prom
#
# AWS-touching helpers (SG / Instance / Tags / Launch) land in subsequent
# slices (Phase B step 6c+). This file establishes the namespace.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.aws.Stack__Naming                            import Stack__Naming


TAG_PURPOSE_KEY     = 'sg:purpose'
TAG_PURPOSE_VALUE   = 'prometheus'
TAG_STACK_NAME_KEY  = 'sg:stack-name'
TAG_ALLOWED_IP_KEY  = 'sg:allowed-ip'
TAG_CREATOR_KEY     = 'sg:creator'
TAG_SECTION_KEY     = 'sg:section'
TAG_SECTION_VALUE   = 'prom'


PROM_NAMING = Stack__Naming(section_prefix='prometheus')                            # AWS Name tag carries 'prometheus-' prefix; never doubled


class Prometheus__AWS__Client(Type_Safe):                                           # Composes the per-concern helpers — kept small on purpose
    pass                                                                            # Helper slots wired in step 6c
