# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: Schema__Content_Proxy__Create__Request
# Create one content-transformation proxy stack. Pure data.
# Secrets (proxyauth, CA key) are carried only to be written to .env / mounted
# files by the user-data builder — they are never persisted in a tag.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sg_compute.platforms.ec2.primitives.Safe_Str__AMI__Id                          import Safe_Str__AMI__Id
from sg_compute.primitives.Safe_Str__AWS__Region                                    import Safe_Str__AWS__Region
from sg_compute.primitives.Safe_Str__Docker__Image                                  import Safe_Str__Docker__Image

from sg_compute_specs.content_proxy.collections.List__Schema__Content_Proxy__Vault__Source import List__Schema__Content_Proxy__Vault__Source
from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Edge                  import Enum__Content_Proxy__Edge
from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Mode                  import Enum__Content_Proxy__Mode
from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Proxy__Tool           import Enum__Content_Proxy__Proxy__Tool
from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Tls                   import Enum__Content_Proxy__Tls
from sg_compute_specs.content_proxy.primitives.Safe_Str__Content_Proxy__Env__File   import Safe_Str__Content_Proxy__Env__File
from sg_compute_specs.content_proxy.primitives.Safe_Str__Content_Proxy__Ref          import Safe_Str__Content_Proxy__Ref
from sg_compute_specs.content_proxy.primitives.Safe_Str__Content_Proxy__Stack__Name  import Safe_Str__Content_Proxy__Stack__Name
from sg_compute_specs.content_proxy.primitives.Safe_Str__IP__Address                 import Safe_Str__IP__Address


class Schema__Content_Proxy__Create__Request(Type_Safe):
    stack_name         : Safe_Str__Content_Proxy__Stack__Name
    region             : Safe_Str__AWS__Region
    instance_type      : Safe_Str__Text  = 't3.large'
    caller_ip          : Safe_Str__IP__Address
    max_hours          : float           = 1.0                                       # fractional ok (0.2 / 0.5 / 1.5)
    mode               : Enum__Content_Proxy__Mode = Enum__Content_Proxy__Mode.DIRECT_PROXY
    tls                : Enum__Content_Proxy__Tls  = Enum__Content_Proxy__Tls.NONE
    edge               : Enum__Content_Proxy__Edge = Enum__Content_Proxy__Edge.NONE   # NONE=vault-as-edge; CADDY=dedicated edge
    firefox_count      : int = 0                                                      # N interactive Firefox browsers → cp-firefox-{n} at /browser/firefox/{n}; >0 forces edge=CADDY
    hostname           : Safe_Str__Content_Proxy__Ref                                 # <slug>.sg-compute.sgraph.ai (Caddy auto-ACME)
    with_aws_dns       : bool = False                                                 # Route 53 upsert <stack>.<zone>→IP at create
    proxy_tool         : Enum__Content_Proxy__Proxy__Tool = Enum__Content_Proxy__Proxy__Tool.MITMDUMP   # prod-safe default
    from_ami           : Safe_Str__AMI__Id                                           # blank → latest AL2023
    use_spot           : bool = True
    disk_size_gb       : int  = 0
    # secrets / operator-supplied material (→ .env or mounted files; never tagged)
    proxyauth_user     : Safe_Str__Text                                              # mitmproxy-ext basic-auth user
    proxyauth_pass     : Safe_Str__Text                                              # mitmproxy-ext basic-auth pass
    proxy_ca_cert      : Safe_Str__Content_Proxy__Ref                                # user-supplied proxy CA cert path
    proxy_ca_key       : Safe_Str__Content_Proxy__Ref                                # user-supplied proxy CA key  path
    proxy_ca_pem       : Safe_Str__Content_Proxy__Env__File                          # combined mitmproxy CA (cert+key) shipped to the box
    scripts_bucket     : Safe_Str__Content_Proxy__Ref                                # CACHE__SERVICE__BUCKET_NAME (MITM scripts)
    forward_aws_creds  : bool = False                                                # bake operator AWS_* into the EC2 .env (parity; else instance role)
    env_inline         : Safe_Str__Content_Proxy__Env__File                          # full .env shipped verbatim (MVP: overrides generated env)
    # image refs (pulled from Docker Hub)
    mitmproxy_image    : Safe_Str__Docker__Image = 'mitmproxy/mitmproxy:12.2.3'
    mitm_service_image : Safe_Str__Docker__Image = 'diniscruz/mgraph-ai-service-mitmproxy'
    playwright_image   : Safe_Str__Docker__Image = 'diniscruz/sg-playwright'
    vault_app_image    : Safe_Str__Docker__Image = 'diniscruz/sg-send-vault'
    # vaults (empty in MVP)
    vaults_to_load     : List__Schema__Content_Proxy__Vault__Source
