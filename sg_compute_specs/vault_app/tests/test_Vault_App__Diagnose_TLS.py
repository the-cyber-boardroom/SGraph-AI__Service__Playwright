# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Vault_App__Service.diagnose() on a healthy TLS stack
# Reproduces the `--wait` hang: a fully-healthy TLS stack where vault-http probed
# :8080 (vault binds :443) and cert-init read an empty stage file (image doesn't
# write it) — both false WARNs that never reached OK. The fixes use :443 + the
# cert-init container's exit status, so both go OK and --wait completes.
# ═══════════════════════════════════════════════════════════════════════════════

from types import SimpleNamespace

from sg_compute_specs.vault_app.service.Vault_App__Service import Vault_App__Service


class _Svc(Vault_App__Service):
    def get_stack_info(self, region, name):
        return SimpleNamespace(state='running', container_engine='docker',
                               with_playwright=True, tls_enabled=True)

    def exec(self, region, name, cmd, timeout_sec=30):
        def out(s): return SimpleNamespace(stdout=s)
        if 'echo ok'                 in cmd: return out('ok')
        if 'sg-compute-boot-failed'  in cmd: return out('NO')
        if 'is-active'               in cmd: return out('active')
        if 'images --format'         in cmd: return out('diniscruz/sg-send-vault\n'
                                                        'diniscruz/sg-host-control\n'
                                                        'diniscruz/sg-playwright\n'
                                                        'mitmproxy/mitmproxy')
        if 'name=cert-init'          in cmd: return out('Exited (0)')          # container succeeded
        if 'cert-init.stage'         in cmd: return out('')                    # ← empty stage file (the bug)
        if 'ps --format'             in cmd: return out('vault-app-sg-send-vault-1  Up 5 minutes\n'
                                                        'vault-app-sg-playwright-1  Up 5 minutes\n'
                                                        'vault-app-host-plane-1  Up 6 minutes\n'
                                                        'vault-app-agent-mitmproxy-1  Up 6 minutes')
        if 'https://127.0.0.1/info/health' in cmd: return out('200')          # TLS vault on :443
        if 'http://127.0.0.1:8080'   in cmd: return out('000')                # must NOT be used for a TLS stack
        if 'sg-compute-boot-ok'      in cmd: return out('YES')
        return out('')


def _final(region='eu-west-2', name='swift-watt'):
    rows = {}
    for n, status, detail in _Svc().diagnose(region, name):
        if status != 'checking':
            rows[n] = (status, detail)
    return rows


class TestDiagnoseTLS:

    def test_vault_http_ok_via_443_on_tls_stack(self):
        rows = _final()
        status, detail = rows['vault-http']
        assert status == 'ok'                    # was 'warn HTTP 000000' before the fix
        assert ':443' in detail

    def test_cert_init_ok_from_container_exit_despite_empty_stage_file(self):
        rows = _final()
        status, detail = rows['cert-init']
        assert status == 'ok'                    # was 'warn — stage file empty' before the fix
        assert 'exited 0' in detail.lower()

    def test_whole_tls_stack_reaches_all_ok(self):
        rows = _final()
        # every emitted check is ok or skip → `--wait` would complete (no hang)
        assert all(s in ('ok', 'skip') for s, _ in rows.values()), rows
