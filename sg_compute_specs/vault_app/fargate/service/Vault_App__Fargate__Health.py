# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute_specs vault_app/fargate — Vault_App__Fargate__Health
# HTTP health poller — extracted pattern from Cli__Vault_Publish wake probe.
# Adaptive backoff: initial_delay → grows to max_delay.  Capped by
# timeout_seconds.  _http_get is injectable for tests (no mock/patch needed).
# ═══════════════════════════════════════════════════════════════════════════════

import time

from typing import Any

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute_specs.vault_app.fargate.schemas.Schema__VAF__Health__Result import Schema__VAF__Health__Result


class Vault_App__Fargate__Health(Type_Safe):
    timeout_seconds : int   = 30
    initial_delay   : float = 0.5
    max_delay       : float = 2.0
    _http_get       : Any    = None                                             # override in tests: (url, headers) → (status_code, ok)

    def _do_get(self, url: str, headers: dict) -> tuple:                       # (status_code, ok)
        if self._http_get:
            return self._http_get(url, headers)
        import urllib.request, urllib.error
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status, True
        except urllib.error.HTTPError as exc:
            return exc.code, False
        except Exception:
            return 0, False

    def wait_for(self, url: str, access_token: str = '') -> Schema__VAF__Health__Result:  # poll until 2xx or timeout
        headers  = {}
        if access_token:
            headers['Authorization'] = f'Bearer {access_token}'
        t_start  = time.monotonic()
        deadline = t_start + self.timeout_seconds
        delay    = self.initial_delay
        attempts = 0
        last_error  = ''
        last_status = 0
        while True:
            attempts    += 1                                                    # always make at least one attempt
            status_code, ok = self._do_get(url, headers)
            last_status  = status_code
            if ok and 200 <= status_code < 300:
                return Schema__VAF__Health__Result(
                    ok          = True,
                    status_code = status_code,
                    attempts    = attempts,
                    duration_ms = int((time.monotonic() - t_start) * 1000),
                    last_error  = '',
                    url         = url,
                )
            last_error = f'HTTP {status_code}' if status_code else 'connection error'
            now = time.monotonic()
            if now >= deadline:                                                 # check timeout after attempt
                return Schema__VAF__Health__Result(
                    ok          = False,
                    status_code = last_status,
                    attempts    = attempts,
                    duration_ms = int((now - t_start) * 1000),
                    last_error  = last_error,
                    url         = url,
                )
            remaining    = deadline - time.monotonic()
            actual_sleep = min(delay, remaining) if remaining > 0 else 0
            if actual_sleep > 0:
                time.sleep(actual_sleep)
            delay = min(delay * 1.5, self.max_delay)                           # adaptive backoff
