# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-app: Vault_App__Stack__Mapper
# Maps a raw boto3 DescribeInstances dict → Schema__Vault_App__Info.
# ═══════════════════════════════════════════════════════════════════════════════

from datetime import datetime, timezone

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute.platforms.ec2.helpers.EC2__Stack__Mapper import (tag_value      ,
                                                                  state_str     ,
                                                                  uptime_seconds,
                                                                  first_sg_id   )
from sg_compute.platforms.ec2.helpers.EC2__Tags__Builder import TAG_STACK_NAME
from sg_compute_specs.vault_app.schemas.Schema__Vault_App__Info import Schema__Vault_App__Info

TAG_WITH_PLAYWRIGHT = 'StackWithPlaywright'
TAG_ENGINE          = 'StackEngine'
TAG_TERMINATE_AT    = 'TerminateAt'
TAG_TLS_ENABLED     = 'StackTLS'                  # 'true' when --with-tls-check; drives the vault_url scheme
TAG_TLS_HOSTNAME    = 'StackTlsHostname'          # FQDN the LE cert was issued for (letsencrypt-hostname mode); empty otherwise.
                                                  # Drives the vault_url *host* — must match the cert SAN or browsers reject.
TAG_ACCESS_TOKEN    = 'AccessToken'               # vault API key + access token (same value, two headers).
                                                  # Note: ec2:DescribeInstances exposes this; the access token was
                                                  # already recoverable on the box via SSM, this just makes the
                                                  # AWS-API path explicit so `sp vault-app info` can surface it.
STACK_TYPE          = 'vault-app'

VAULT_PORT               = 8080
PLAYWRIGHT_EXTERNAL_PORT = 80                     # host:80 → container:8000 — standard port so Claude/sandbox egress proxies (which only allow :80/:443) can reach it
HOST_PLANE_LOCAL_PORT    = 19009                  # 127.0.0.1:19009 → host-plane:8000 — SSM-port-forward target only
MITMWEB_LOCAL_PORT       = 19081                  # 127.0.0.1:19081 → agent-mitmproxy:8000 (admin FastAPI, with Routes__Web /web/* → mitmweb)


def _time_remaining(details: dict) -> tuple:
    raw = tag_value(details, TAG_TERMINATE_AT) or ''
    if not raw:
        return '', 0
    try:
        t         = datetime.fromisoformat(raw.replace('Z', '+00:00'))
        remaining = int((t - datetime.now(timezone.utc)).total_seconds())
        return raw, max(0, remaining)
    except Exception:
        return raw, 0


class Vault_App__Stack__Mapper(Type_Safe):

    def to_info(self, details: dict, region: str) -> Schema__Vault_App__Info:
        public_ip               = details.get('PublicIpAddress', '') or ''
        terminate_at, remaining = _time_remaining(details)
        tls_on                  = tag_value(details, TAG_TLS_ENABLED)     == 'true'
        with_playwright         = tag_value(details, TAG_WITH_PLAYWRIGHT) == 'true'
        tls_hostname            = tag_value(details, TAG_TLS_HOSTNAME) or ''
        # The cert host: hostname when LE was issued for an FQDN, the IP otherwise.
        # Browsers (and Anthropic's egress proxy) reject mismatches strictly, so the URL
        # surfaced to operators MUST match the cert SAN.
        cert_host = tls_hostname if tls_hostname else public_ip
        if public_ip:
            vault_url      = (f'https://{cert_host}' if tls_on
                              else f'http://{public_ip}:{VAULT_PORT}')
            # Omit the :80 suffix — it's the default HTTP port and 'http://host' is cleaner / more sandbox-friendly.
            port_suffix    = '' if PLAYWRIGHT_EXTERNAL_PORT == 80 else f':{PLAYWRIGHT_EXTERNAL_PORT}'
            # Playwright is plain HTTP; the hostname still works (resolves to the IP, no cert involved).
            # Prefer the hostname so a single base URL covers both sandbox and laptop callers.
            playwright_host = tls_hostname or public_ip
            playwright_url  = f'http://{playwright_host}{port_suffix}' if with_playwright else ''
        else:
            vault_url, playwright_url = '', ''
        instance_id    = details.get('InstanceId', '') or ''
        host_plane_url = f'http://localhost:{HOST_PLANE_LOCAL_PORT}' if instance_id else ''
        mitmweb_url    = (f'http://localhost:{MITMWEB_LOCAL_PORT}/web/'
                          if instance_id and with_playwright else '')

        def _ssm_fwd(port: int) -> str:
            return (f'aws ssm start-session --target {instance_id} '
                    f'--document-name AWS-StartPortForwardingSession '
                    f'--parameters \'{{"portNumber":["{port}"],'
                    f'"localPortNumber":["{port}"]}}\' '
                    f'--region {region}') if instance_id else ''

        ssm_forward         = _ssm_fwd(HOST_PLANE_LOCAL_PORT)
        mitmweb_ssm_forward = _ssm_fwd(MITMWEB_LOCAL_PORT) if with_playwright else ''
        return Schema__Vault_App__Info(
            instance_id        = instance_id                                         ,
            stack_name         = tag_value(details, TAG_STACK_NAME)                  ,
            region             = region                                              ,
            state              = state_str(details)                                  ,
            public_ip          = public_ip                                           ,
            private_ip         = details.get('PrivateIpAddress', '') or ''            ,
            instance_type      = details.get('InstanceType', '')                     ,
            ami_id             = details.get('ImageId', '')                          ,
            security_group_id  = first_sg_id(details)                                ,
            vault_url          = vault_url                                            ,
            playwright_url     = playwright_url                                       ,
            host_plane_url      = host_plane_url                                      ,
            mitmweb_url         = mitmweb_url                                         ,
            ssm_forward         = ssm_forward                                         ,
            mitmweb_ssm_forward = mitmweb_ssm_forward                                 ,
            tls_enabled        = tls_on                                               ,
            with_playwright    = with_playwright                                      ,
            container_engine   = tag_value(details, TAG_ENGINE)                      ,
            access_token       = tag_value(details, TAG_ACCESS_TOKEN)                 ,
            uptime_seconds     = uptime_seconds(details)                              ,
            spot               = details.get('InstanceLifecycle', '') == 'spot'      ,
            terminate_at       = terminate_at                                         ,
            time_remaining_sec = remaining                                            ,
        )
