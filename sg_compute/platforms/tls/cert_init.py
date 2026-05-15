# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — cert_init
# Entry point for the one-shot cert sidecar. Generates a self-signed cert+key,
# writes them to the shared /certs volume, and exits — the TLS apps that read
# the cert are gated behind this via compose `depends_on: service_completed_successfully`.
#
#   python -m sg_compute.platforms.tls.cert_init
#
# Common name resolution order:
#   1. SG__CERT_INIT__COMMON_NAME env
#   2. the instance's public IPv4 from EC2 IMDSv2
#   3. 'localhost'
# Cert/key paths follow the same env contract the TLS apps read.
# ═══════════════════════════════════════════════════════════════════════════════

import os
import urllib.request

from sg_compute.platforms.tls.Cert__Generator import Cert__Generator

ENV__COMMON_NAME = 'SG__CERT_INIT__COMMON_NAME'
ENV__SANS        = 'SG__CERT_INIT__SANS'
ENV__CERT_FILE   = 'FAST_API__TLS__CERT_FILE'
ENV__KEY_FILE    = 'FAST_API__TLS__KEY_FILE'

DEFAULT__CERT_FILE   = '/certs/cert.pem'
DEFAULT__KEY_FILE    = '/certs/key.pem'
DEFAULT__COMMON_NAME = 'localhost'

_IMDS_BASE = 'http://169.254.169.254/latest'


def _imds_public_ipv4() -> str:                                              # best-effort IMDSv2 lookup; '' on any failure
    try:
        token_req = urllib.request.Request(f'{_IMDS_BASE}/api/token', method='PUT',
                                           headers={'X-aws-ec2-metadata-token-ttl-seconds': '60'})
        token     = urllib.request.urlopen(token_req, timeout=2).read().decode()
        ip_req    = urllib.request.Request(f'{_IMDS_BASE}/meta-data/public-ipv4',
                                           headers={'X-aws-ec2-metadata-token': token})
        return urllib.request.urlopen(ip_req, timeout=2).read().decode().strip()
    except Exception:
        return ''


def resolve_common_name() -> str:
    return (os.environ.get(ENV__COMMON_NAME, '').strip()
            or _imds_public_ipv4()
            or DEFAULT__COMMON_NAME)


def main() -> None:
    cert_path   = os.environ.get(ENV__CERT_FILE) or DEFAULT__CERT_FILE
    key_path    = os.environ.get(ENV__KEY_FILE)  or DEFAULT__KEY_FILE
    common_name = resolve_common_name()
    sans        = [s.strip() for s in os.environ.get(ENV__SANS, '').split(',') if s.strip()]

    Cert__Generator().generate_to_files(cert_path   = cert_path   ,
                                        key_path    = key_path    ,
                                        common_name = common_name ,
                                        sans        = sans        )
    print(f'[cert-init] self-signed cert written: cn={common_name!r} '
          f'cert={cert_path} key={key_path} sans={sans}')


if __name__ == '__main__':
    main()
