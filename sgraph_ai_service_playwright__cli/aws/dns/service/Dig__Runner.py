# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Dig__Runner
# Thin subprocess wrapper around the `dig` CLI. Every call sets LC_ALL=C so
# output is always in English regardless of system locale. Keeps all subprocess
# interaction isolated so callers can substitute a fake in tests.
# ═══════════════════════════════════════════════════════════════════════════════

import os
import subprocess
import time

from osbot_utils.type_safe.Type_Safe                                                 import Type_Safe

from sgraph_ai_service_playwright__cli.aws.dns.schemas.Schema__Dig__Result           import Schema__Dig__Result


class Dig__Runner(Type_Safe):                                                    # Subprocess wrapper for dig — one seam for tests to override

    def run(self, nameserver: str, name: str, rtype: str,
            no_recurse: bool = False, timeout: int = 5) -> Schema__Dig__Result: # Build and run a dig command; return a typed result
        cmd = ['dig']
        if nameserver:                                                            # Empty nameserver => let dig use the host's default resolver
            cmd.append(f'@{nameserver}')
        cmd += ['+short', name, rtype]
        if no_recurse:
            cmd.append('+norecurse')
        env = {'LC_ALL': 'C', **os.environ}                                     # LC_ALL=C ensures English output; preserve PATH and rest of environ
        start = time.monotonic()
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True,
                                  timeout=timeout, env=env)
            duration_ms = int((time.monotonic() - start) * 1000)
            lines       = [l.strip() for l in proc.stdout.splitlines() if l.strip()]
            return Schema__Dig__Result(nameserver  = nameserver        ,
                                       name        = name              ,
                                       rtype       = rtype             ,
                                       values      = lines             ,
                                       exit_code   = proc.returncode   ,
                                       error       = proc.stderr.strip(),
                                       duration_ms = duration_ms       )
        except subprocess.TimeoutExpired:
            duration_ms = int((time.monotonic() - start) * 1000)
            return Schema__Dig__Result(nameserver  = nameserver                     ,
                                       name        = name                           ,
                                       rtype       = rtype                          ,
                                       values      = []                             ,
                                       exit_code   = 1                              ,
                                       error       = f'timed out after {timeout}s' ,
                                       duration_ms = duration_ms                    )
        except FileNotFoundError:
            return Schema__Dig__Result(nameserver  = nameserver              ,
                                       name        = name                    ,
                                       rtype       = rtype                   ,
                                       values      = []                      ,
                                       exit_code   = 1                       ,
                                       error       = 'dig not found in PATH' ,
                                       duration_ms = 0                       )

    def check_available(self) -> bool:                                           # Returns False if dig is not installed / not on PATH
        try:
            subprocess.run(['dig', '-v'], capture_output=True, timeout=3)
            return True
        except FileNotFoundError:
            return False
