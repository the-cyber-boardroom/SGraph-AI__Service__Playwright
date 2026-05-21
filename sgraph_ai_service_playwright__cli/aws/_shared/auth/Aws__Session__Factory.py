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
    from sgraph_ai_service_playwright__cli.aws._shared.auth                import AWS__Auth__Context
    from sgraph_ai_service_playwright__cli.aws._shared.auth.AWS__Auth__Resolver import AWS__Auth__Resolver
    family = AWS__Auth__Context.get_active_family()
    if family:                                                                       # a command family is running → assume its scoped role transparently
        client = AWS__Auth__Resolver().client_for_family(family, service, region=region)
        if client is not None:
            return client                                                            # else: fall back to the base identity (guard surfaces a menu if it too lacks access)
    return Sg__Aws__Session.from_context().boto3_client_from_context(service, region=region)
