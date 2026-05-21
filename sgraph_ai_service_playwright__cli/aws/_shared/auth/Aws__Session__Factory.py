# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — aws shared auth: Aws__Session__Factory
# The one place a boto3 client is born for the whole `sg aws *` surface. Everything
# routes through Sg__Aws__Session (keyring role → STS AssumeRole → cached temp creds,
# with a bare-boto3 fall-through when no role is selected — safe on Fargate/Lambda IMDS
# and on CI). Clients that historically called boto3.client() directly (CloudFront,
# Logs, Firehose, the LETS S3 boundaries) now call this from their existing seam, so
# the credential layer + the auth-error guard (P2) cover every command uniformly.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.credentials.service.Sg__Aws__Session import Sg__Aws__Session


def boto3_client_via_context(service : str, region : str = ''):
    return Sg__Aws__Session.from_context().boto3_client_from_context(service, region=region)
