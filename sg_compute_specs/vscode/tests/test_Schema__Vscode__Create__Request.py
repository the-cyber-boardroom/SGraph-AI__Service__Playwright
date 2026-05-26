# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vscode: Schema__Vscode__Create__Request tests
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sg_compute_specs.vscode.enums.Enum__Vscode__Distribution        import Enum__Vscode__Distribution
from sg_compute_specs.vscode.enums.Enum__Vscode__Ingress             import Enum__Vscode__Ingress
from sg_compute_specs.vscode.schemas.Schema__Vscode__Create__Request import Schema__Vscode__Create__Request


class test_Schema__Vscode__Create__Request(TestCase):

    def test_defaults(self):
        r = Schema__Vscode__Create__Request()
        assert r.region        == 'eu-west-2'
        assert r.instance_type == 't3.large'
        assert r.max_hours     == 4.0
        assert r.use_spot      is True
        assert int(r.disk_size_gb) == 100
        assert r.distribution  == Enum__Vscode__Distribution.CODE_SERVER
        assert r.ingress       == Enum__Vscode__Ingress.SSM_FORWARD

    def test_enum_values(self):
        assert Enum__Vscode__Distribution('code-server') == Enum__Vscode__Distribution.CODE_SERVER
        assert Enum__Vscode__Distribution('serve-web')   == Enum__Vscode__Distribution.SERVE_WEB
        assert Enum__Vscode__Ingress('ssm-forward')      == Enum__Vscode__Ingress.SSM_FORWARD
        assert Enum__Vscode__Ingress('public-https')     == Enum__Vscode__Ingress.PUBLIC_HTTPS

    def test_json_round_trip(self):
        r       = Schema__Vscode__Create__Request(stack_name='brave-fermi', max_hours=2.0)
        restored = Schema__Vscode__Create__Request.from_json(r.json())
        assert restored.stack_name == 'brave-fermi'
        assert restored.max_hours  == 2.0
        assert restored.ingress    == Enum__Vscode__Ingress.SSM_FORWARD
