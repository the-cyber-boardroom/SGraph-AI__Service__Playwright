# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Enum__Deployment__Target
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Deployment__Target(str, Enum):                                          # Where the service is running
    LAPTOP     = "laptop"                                                           # Direct uvicorn / docker run
    CI         = "ci"                                                               # GitHub Actions or similar
    CLAUDE_WEB = "claude_web"                                                       # Running inside a Claude session
    CONTAINER  = "container"                                                        # Generic docker/K8s/Fargate
    LAMBDA     = "lambda"                                                           # AWS Lambda container

    def __str__(self): return self.value
