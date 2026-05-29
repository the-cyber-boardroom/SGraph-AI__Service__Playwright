# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Vault_App__Interceptor__Resolver
# none → no-op; inline → (source, 'inline'); empty inline → error.
# ═══════════════════════════════════════════════════════════════════════════════

import pytest

from sg_compute_specs.vault_app.enums.Enum__Vault_App__Interceptor__Kind        import Enum__Vault_App__Interceptor__Kind
from sg_compute_specs.vault_app.schemas.Schema__Vault_App__Interceptor__Choice  import Schema__Vault_App__Interceptor__Choice
from sg_compute_specs.vault_app.service.Vault_App__Interceptor__Resolver        import (Vault_App__Interceptor__Resolver,
                                                                                        NO_OP_SOURCE                   )

SCRIPT = ('from mitmproxy import http\n\n\n'
          "def request(flow: http.HTTPFlow) -> None:\n"
          "    flow.request.headers['X-Sg-Vault-App'] = 'on'\n")


class TestVaultAppInterceptorResolver:

    def test_default_choice_is_no_op(self):
        source, label = Vault_App__Interceptor__Resolver().resolve()
        assert source == NO_OP_SOURCE
        assert label  == ''

    def test_kind_none_is_no_op(self):
        choice        = Schema__Vault_App__Interceptor__Choice(kind=Enum__Vault_App__Interceptor__Kind.NONE)
        source, label = Vault_App__Interceptor__Resolver().resolve(choice)
        assert source == NO_OP_SOURCE
        assert label  == ''

    def test_inline_returns_source(self):
        choice        = Schema__Vault_App__Interceptor__Choice(kind=Enum__Vault_App__Interceptor__Kind.INLINE,
                                                               inline_source=SCRIPT)
        source, label = Vault_App__Interceptor__Resolver().resolve(choice)
        assert source == SCRIPT
        assert label  == 'inline'

    def test_inline_without_source_raises(self):
        choice = Schema__Vault_App__Interceptor__Choice(kind=Enum__Vault_App__Interceptor__Kind.INLINE)
        with pytest.raises(ValueError, match='non-empty inline_source'):
            Vault_App__Interceptor__Resolver().resolve(choice)
