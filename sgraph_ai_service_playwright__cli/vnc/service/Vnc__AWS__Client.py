# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Vnc__AWS__Client
# Composition shell for the per-concern AWS helpers (SG / AMI / Instance /
# Tags / Launch). Mirrors OpenSearch__AWS__Client + Prometheus__AWS__Client.
# Owns the tag-key constants and the VNC_NAMING binding so the section's
# AWS surface lives in one shared header.
#
# Tag convention (mirrors elastic + os + prom):
#   sg:purpose      : vnc
#   sg:stack-name   : {stack_name}                 ← logical name lookup
#   sg:allowed-ip   : {caller_ip}                  ← records what /32 was set
#   sg:creator      : git email or $USER
#   sg:section      : vnc
#   sg:interceptor  : <name | inline | none>       ← per N5; set in Tags__Builder
#
# AWS-touching helpers (SG / AMI / Instance / Tags / Launch) land in
# subsequent slices. This file establishes the namespace.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.aws.Stack__Naming                            import Stack__Naming


TAG_PURPOSE_KEY      = 'sg:purpose'
TAG_PURPOSE_VALUE    = 'vnc'
TAG_STACK_NAME_KEY   = 'sg:stack-name'
TAG_ALLOWED_IP_KEY   = 'sg:allowed-ip'
TAG_CREATOR_KEY      = 'sg:creator'
TAG_SECTION_KEY      = 'sg:section'
TAG_SECTION_VALUE    = 'vnc'
TAG_INTERCEPTOR_KEY  = 'sg:interceptor'                                             # N5: 'none' | 'name:<example>' | 'inline' — recorded for `sp vnc info`
TAG_INTERCEPTOR_NONE = 'none'


VNC_NAMING = Stack__Naming(section_prefix='vnc')                                    # AWS Name tag carries 'vnc-' prefix; never doubled


class Vnc__AWS__Client(Type_Safe):                                                  # Composes the per-concern helpers — kept small on purpose
    pass                                                                            # Helper slots wired in step 7c
