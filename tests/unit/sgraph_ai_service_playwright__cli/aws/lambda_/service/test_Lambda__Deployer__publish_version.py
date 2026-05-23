# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Lambda__Deployer.publish_version (numbered version for L@E)
# ═══════════════════════════════════════════════════════════════════════════════

from tests.unit.sgraph_ai_service_playwright__cli.aws.lambda_.service.Lambda__AWS__Client__In_Memory import Lambda__AWS__Client__In_Memory, Lambda__Deployer__In_Memory
from sgraph_ai_service_playwright__cli.aws.lambda_.schemas.Schema__Lambda__Deploy__Request           import Schema__Lambda__Deploy__Request


def _deployer():
    return Lambda__Deployer__In_Memory(Lambda__AWS__Client__In_Memory())


def _deploy(d, name='sg-sentinel-l2'):
    return d.deploy_from_folder(Schema__Lambda__Deploy__Request(name=name, folder_path='/tmp/x',
                                                                handler='lambda_handler.handler', role_arn='arn:aws:iam::1:role/r'))


class TestPublishVersion:
    def test_publish_returns_numbered_version_arn(self):
        d = _deployer()
        _deploy(d)
        arn = d.publish_version('sg-sentinel-l2')
        assert arn.endswith(':1')                                                    # numbered version (not $LATEST)

    def test_publish_increments(self):
        d = _deployer()
        _deploy(d)
        d.publish_version('sg-sentinel-l2')
        assert d.publish_version('sg-sentinel-l2').endswith(':2')
