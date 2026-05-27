# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Vault_App__Reverse_Proxy__Override
# The override write-block must ship three importable files and stay heredoc-safe.
# ═══════════════════════════════════════════════════════════════════════════════

from sg_compute_specs.vault_app.service.Vault_App__Reverse_Proxy__Override import (Vault_App__Reverse_Proxy__Override,
                                                                                   SERVE_WITH_PROXY                 ,
                                                                                   OVERRIDES_DIR                    )


class TestVaultAppReverseProxyOverride:

    def test_serve_with_proxy_is_valid_python(self):
        compile(SERVE_WITH_PROXY, 'serve_with_proxy.py', 'exec')                    # must parse — it runs as the container entrypoint

    def test_serve_with_proxy_wraps_stock_boot(self):
        assert 'from sgraph_ai_app_send__docker.app import create_app'                 in SERVE_WITH_PROXY
        assert 'Fast_API__TLS__Launcher'                                               in SERVE_WITH_PROXY
        assert 'from sg_overrides.Fast_API__Reverse_Proxy import Fast_API__Reverse_Proxy' in SERVE_WITH_PROXY
        assert 'create_app()'                                                          in SERVE_WITH_PROXY

    def test_shipped_proxy_source_is_valid_python(self):
        src = Vault_App__Reverse_Proxy__Override().reverse_proxy_source()
        compile(src, 'Fast_API__Reverse_Proxy.py', 'exec')
        assert 'class Fast_API__Reverse_Proxy' in src

    def test_write_block_ships_three_files(self):
        block = Vault_App__Reverse_Proxy__Override().render_write_block()
        assert f'{OVERRIDES_DIR}/__init__.py'               in block
        assert f'{OVERRIDES_DIR}/Fast_API__Reverse_Proxy.py' in block
        assert f'{OVERRIDES_DIR}/serve_with_proxy.py'        in block
        assert f'mkdir -p {OVERRIDES_DIR}'                   in block

    def test_write_block_is_heredoc_safe(self):
        block = Vault_App__Reverse_Proxy__Override().render_write_block()
        # The quoted delimiter must open and close an even number of times and
        # never appear inside a payload (which would truncate the heredoc).
        assert block.count("<<'SG_OVERRIDE_EOF'") == 3
        assert block.count('\nSG_OVERRIDE_EOF')   == 3

    def test_write_block_uses_quoted_heredoc(self):
        block = Vault_App__Reverse_Proxy__Override().render_write_block()
        assert "<<'SG_OVERRIDE_EOF'" in block                                       # quoted → shell never expands the Python payload
