# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge local: sg_edge_local__config
# Hard-coded edge domains + local-stack state paths (Phase 1 local deployment).
#
#   AWS edge zone   : *.edge.sg-labs.app    — the create/destroy-at-will distribution
#                     + Route 53 zone the live edge uses (one CloudFront dist, one
#                     wildcard ACM cert). Hard-coded so every `sg edge` command
#                     defaults to it; nothing else in the account is touched.
#   Local edge zone : *.edge.sg-labs.local  — the local DNS zone the local stack
#                     serves. Resolves to 127.0.0.1; no AWS, no network.
#
# Local stack state lives on disk (each `sg edge local *` command is a separate
# process, so the DNS registry + stack marker must persist between invocations):
#   <state_dir>/dns.json    file-backed DNS registry (the "local DNS server")
#   <state_dir>/stack.json  stack marker (deployed? parent, created_at)
# state_dir defaults to ~/.sg/edge_local and is overridable via
# $SG_EDGE__LOCAL_STATE_DIR (tests point it at a temp dir).
# ═══════════════════════════════════════════════════════════════════════════════

import os

SG_EDGE__AWS_PARENT   = 'edge.sg-labs.app'                                            # hard-coded AWS edge zone (create/destroy at will)
SG_EDGE__LOCAL_PARENT = 'edge.sg-labs.local'                                          # local DNS zone for the local stack

LOCAL_PROXY_IP        = '127.0.0.1'                                                   # the local proxy "fleet IP"
LOCAL_BACKEND_IP      = '127.0.0.1'                                                   # the local slug-backend IP written into _sg.<slug> TXT
LOCAL_BACKEND_PORT    = 8080                                                          # the local slug-backend port
LOCAL_SERVE_PORT      = 8410                                                          # default port for `sg edge local serve`


def local_state_dir() -> str:
    return os.environ.get('SG_EDGE__LOCAL_STATE_DIR', os.path.expanduser('~/.sg/edge_local'))


def local_dns_path() -> str:
    return os.path.join(local_state_dir(), 'dns.json')


def local_stack_path() -> str:
    return os.path.join(local_state_dir(), 'stack.json')
