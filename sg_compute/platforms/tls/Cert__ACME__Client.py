# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Cert__ACME__Client
# Issues a publicly-trusted Let's Encrypt certificate for *either* an EC2 IP
# address *or* a DNS hostname, via the ACME protocol (RFC 8555) http-01 challenge.
#
#   - IP-address certs went GA at Let's Encrypt in Jan 2026; they require the
#     'shortlived' profile (~6-day validity). make_csr(..., ipaddrs=[...]).
#   - DNS-name certs use the default LE profile (90-day validity); make_csr(..., domains=[...]).
#   - http-01 (not tls-alpn-01): the challenge is a single file served over :80
#     by ACME__Challenge__Server. Works identically for both IP and hostname
#     SAN types — the SAN type only changes what's signed, not how it's validated.
#   - Issue-only, no renewal — ephemeral stacks outlive no cert (see the v0.2.6
#     TLS architecture doc §8.1).
#
# The `acme` / `josepy` imports are deferred into issue() so this module stays
# importable (and the non-network helpers stay testable) without them present.
# The network dance against Let's Encrypt cannot be exercised in-sandbox; it is
# verified by a live deploy run.
# ═══════════════════════════════════════════════════════════════════════════════

import ipaddress
import os

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute.platforms.tls.ACME__Challenge__Server import ACME__Challenge__Server
from sg_compute.platforms.tls.Schema__ACME__Config    import Schema__ACME__Config

LE_DIRECTORY__STAGING = 'https://acme-staging-v02.api.letsencrypt.org/directory'
LE_DIRECTORY__PROD    = 'https://acme-v02.api.letsencrypt.org/directory'

ACCOUNT_KEY_BITS = 2048
CERT_KEY_BITS    = 2048
USER_AGENT       = 'sg-cert-init'


class Cert__ACME__Client(Type_Safe):

    def config(self, prod: bool = False, contact_email: str = '', for_hostname: bool = False) -> Schema__ACME__Config:
        # The 'shortlived' profile is IP-cert-only. DNS-name certs use the LE default profile
        # (no profile field on new_order). Clear it explicitly when issuing for a hostname.
        return Schema__ACME__Config(directory_url = LE_DIRECTORY__PROD if prod else LE_DIRECTORY__STAGING ,
                                    contact_email = contact_email                                        ,
                                    profile       = '' if for_hostname else 'shortlived'                 )

    def build_cert_key_pem(self) -> bytes:                                   # the key the issued cert will use
        from cryptography.hazmat.primitives           import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        key = rsa.generate_private_key(public_exponent=65537, key_size=CERT_KEY_BITS)
        return key.private_bytes(encoding             = serialization.Encoding.PEM         ,
                                 format               = serialization.PrivateFormat.PKCS8 ,
                                 encryption_algorithm  = serialization.NoEncryption()      )

    def build_csr(self, cert_key_pem: bytes, ip: str = '', *, hostname: str = '') -> bytes:
        # Exactly one of `ip` or `hostname` — IP SAN for letsencrypt-ip, DNS SAN for letsencrypt-hostname.
        from acme import crypto_util
        if bool(hostname) == bool(ip):
            raise ValueError('build_csr requires exactly one of ip / hostname')
        if hostname:
            return crypto_util.make_csr(cert_key_pem, domains=[hostname])
        return crypto_util.make_csr(cert_key_pem, ipaddrs=[ipaddress.ip_address(ip)])

    def select_http01(self, order):                                          # the http-01 ChallengeBody from an order
        from acme import challenges
        for authz in order.authorizations:
            for challb in authz.body.challenges:
                if isinstance(challb.chall, challenges.HTTP01):
                    return challb
        raise RuntimeError('ACME order offered no http-01 challenge')

    def issue(self, ip          : str                  = ''   ,
                    cert_path   : str                  = ''   ,
                    key_path    : str                  = ''   ,
                    config      : Schema__ACME__Config = None ,
                    *                                         ,
                    hostname    : str                  = ''   ) -> None:
        import josepy
        from acme                                      import client, messages
        from cryptography.hazmat.primitives.asymmetric  import rsa

        if bool(hostname) == bool(ip):
            raise ValueError('issue requires exactly one of ip / hostname')

        config = config or self.config(for_hostname=bool(hostname))

        account_key = josepy.JWKRSA(key=rsa.generate_private_key(public_exponent=65537,
                                                                 key_size=ACCOUNT_KEY_BITS))
        net         = client.ClientNetwork(account_key, user_agent=USER_AGENT)
        directory   = client.ClientV2.get_directory(config.directory_url, net)
        acme_client = client.ClientV2(directory, net=net)
        acme_client.new_account(messages.NewRegistration.from_data(
            email                   = config.contact_email or None ,
            terms_of_service_agreed = True                          ))

        cert_key_pem = self.build_cert_key_pem()
        csr_pem      = self.build_csr(cert_key_pem, ip=ip, hostname=hostname)
        order        = acme_client.new_order(csr_pem, profile=config.profile or None)

        challb               = self.select_http01(order)
        response, validation = challb.chall.response_and_validation(account_key)

        with ACME__Challenge__Server(port=config.challenge_port) as server:
            server.set_challenge(challb.chall.path, validation)
            acme_client.answer_challenge(challb, response)
            finalized = acme_client.poll_and_finalize(order)

        self._write(cert_path, finalized.fullchain_pem)
        self._write(key_path,  cert_key_pem.decode() if isinstance(cert_key_pem, bytes) else cert_key_pem)
        os.chmod(key_path,  0o600)
        os.chmod(cert_path, 0o644)

    def _write(self, path: str, content: str) -> None:
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, 'w') as f:
            f.write(content)
