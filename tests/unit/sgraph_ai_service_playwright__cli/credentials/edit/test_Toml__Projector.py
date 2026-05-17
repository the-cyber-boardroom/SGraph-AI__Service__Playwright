# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Toml__Projector
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__AWS__Region    import Safe_Str__AWS__Region
from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__AWS__Role__ARN import Safe_Str__AWS__Role__ARN
from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__Role__Name     import Safe_Str__Role__Name
from sgraph_ai_service_playwright__cli.credentials.schemas.Schema__AWS__Role__Config   import Schema__AWS__Role__Config
from sgraph_ai_service_playwright__cli.credentials.service.Keyring__Mac__OS            import Keyring__Mac__OS__In_Memory
from sgraph_ai_service_playwright__cli.credentials.service.Credentials__Store          import Credentials__Store
from sgraph_ai_service_playwright__cli.credentials.edit.Toml__Projector                import Toml__Projector
from sgraph_ai_service_playwright__cli.credentials.edit.Schema__Edit__Snapshot         import SENTINEL


def _store() -> Credentials__Store:
    return Credentials__Store(keyring=Keyring__Mac__OS__In_Memory())


def _cfg(name: str, region: str = 'us-east-1') -> Schema__AWS__Role__Config:
    return Schema__AWS__Role__Config(
        name            = Safe_Str__Role__Name(name),
        region          = Safe_Str__AWS__Region(region),
        assume_role_arn = Safe_Str__AWS__Role__ARN(''),
        session_name    = Safe_Str__Role__Name(f'sg-{name}'),
    )


class test_Toml__Projector(TestCase):

    def test_project_empty_store(self):
        store = _store()
        proj  = Toml__Projector(store=store)
        text  = proj.project()
        assert 'SG credentials' in text

    def test_project_contains_role(self):
        store = _store()
        store.role_set(_cfg('default', 'us-east-1'))
        store.aws_credentials_set('default', 'AKIAIOSFODNN7EXAMPLE', 's3cr3t')
        text = Toml__Projector(store=store).project()
        assert '[roles.default]' in text
        assert 'AKIAIOSFODNN7EXAMPLE' in text
        assert SENTINEL in text

    def test_project_masks_non_akia_access_key(self):
        store = _store()
        store.role_set(_cfg('default', 'us-east-1'))
        store.aws_credentials_set('default', 'not-an-akia-key', 's3cr3t')
        text = Toml__Projector(store=store).project()
        assert 'not-an-akia-key' not in text
        assert SENTINEL in text

    def test_snapshot_returns_snapshot_object(self):
        store = _store()
        store.role_set(_cfg('default', 'us-east-1'))
        snap  = Toml__Projector(store=store).snapshot()
        assert 'default' in snap.roles
        assert snap.roles['default']['region'] == 'us-east-1'
