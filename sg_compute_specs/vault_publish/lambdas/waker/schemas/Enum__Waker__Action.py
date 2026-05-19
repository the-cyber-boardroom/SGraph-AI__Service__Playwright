# ═══════════════════════════════════════════════════════════════════════════════
# Waker — Enum__Waker__Action
# What the Lambda did this invocation — X-Waker-Action header value.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Waker__Action(str, Enum):
    NONE             = 'none'
    STARTED_EC2      = 'started-ec2'      # called ec2.start_instances
    PROXIED          = 'proxied'           # forwarded request to vault-app
    RETURNED_WARMING = 'returned-warming'  # returned warming page without mutating
    RETURNED_404     = 'returned-404'      # returned 404 — slug unknown
    PROXY_ERROR      = 'proxy-error'       # proxy returned 5xx or threw

    def __str__(self) -> str:
        return self.value
