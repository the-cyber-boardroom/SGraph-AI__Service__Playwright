# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vscode: Vscode__Service create-time validation
# These guards run before any AWS call, so no setup()/credentials are needed.
# Skips when boto3 (imported transitively by the AWS client) is unavailable.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase, skipUnless

try:
    from sg_compute_specs.vscode.service.Vscode__Service                 import Vscode__Service
    from sg_compute_specs.vscode.schemas.Schema__Vscode__Create__Request import Schema__Vscode__Create__Request
    from sg_compute_specs.vscode.enums.Enum__Vscode__Ingress             import Enum__Vscode__Ingress
    from sg_compute_specs.vscode.enums.Enum__Vscode__Distribution        import Enum__Vscode__Distribution
    IMPORTABLE = True
except Exception:
    IMPORTABLE = False


@skipUnless(IMPORTABLE, 'vscode service deps (boto3) not installed')
class test_Vscode__Service__validation(TestCase):

    def test_with_aws_dns_requires_public_https(self):
        svc = Vscode__Service()                                                     # no setup() — guard runs first
        req = Schema__Vscode__Create__Request(with_aws_dns=True, fqdn='vsc.example.com',
                                              ingress=Enum__Vscode__Ingress.SSM_FORWARD)
        with self.assertRaises(ValueError) as ctx:
            svc.create_stack(req)
        assert 'public-https' in str(ctx.exception)

    def test_with_aws_dns_requires_fqdn(self):
        svc = Vscode__Service()
        req = Schema__Vscode__Create__Request(with_aws_dns=True, fqdn='',
                                              ingress=Enum__Vscode__Ingress.PUBLIC_HTTPS)
        with self.assertRaises(ValueError) as ctx:
            svc.create_stack(req)
        assert 'fqdn' in str(ctx.exception)

    def test_serve_web_rejects_public_https(self):
        svc = Vscode__Service()
        req = Schema__Vscode__Create__Request(distribution=Enum__Vscode__Distribution.SERVE_WEB,
                                              ingress=Enum__Vscode__Ingress.PUBLIC_HTTPS)
        with self.assertRaises(ValueError) as ctx:
            svc.create_stack(req)
        assert 'ssm-forward' in str(ctx.exception)

    def test_openvscode_not_implemented(self):
        svc = Vscode__Service()
        req = Schema__Vscode__Create__Request(distribution=Enum__Vscode__Distribution.OPENVSCODE_SERVER)
        with self.assertRaises(NotImplementedError):
            svc.create_stack(req)
