# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for the CF-env sim server.node.js (the docker container's listener)
# Runs server.node.js with local node against a materialised build context (no docker)
# and asserts BOTH paths return a real verdict: a GET request (curl path) and a POSTed
# captured object (harness path). Guards the "everything allowed" + GET-405 bugs.
# node-gated.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import shutil
import socket
import subprocess
import time
from unittest import TestCase, skipUnless

import requests

from sgraph_ai_service_playwright__cli.sentinel.runtime.layer1.Sentinel__L1__Source     import node_available
from sgraph_ai_service_playwright__cli.sentinel.runtime.local.Sentinel__Docker__Runtime import Sentinel__Docker__Runtime


def _free_port() -> int:
    s = socket.socket(); s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]; s.close(); return port


@skipUnless(node_available(), 'node not available')
class test_CF_Env_Server(TestCase):
    def test_get_and_post_both_return_real_verdicts(self):
        ctx  = Sentinel__Docker__Runtime().build_context()                           # materialised engine + server.node.js
        port = _free_port()
        proc = subprocess.Popen(['node', 'server.node.js'], cwd=ctx, env={'PORT': str(port), 'PATH': __import__('os').environ['PATH']})
        try:
            base = f'http://127.0.0.1:{port}'
            for _ in range(40):                                                      # wait for /health
                try:
                    if requests.get(base + '/health', timeout=1).status_code == 200:
                        break
                except requests.RequestException:
                    time.sleep(0.1)

            # GET path (curl) — the engine evaluates the actual request
            got = requests.get(base + '/etc/passwd', timeout=5).json()
            assert got['verdict'] == 'block' and got['rule_id'] == '0012'

            benign = requests.get(base + '/index.html', timeout=5).json()
            assert benign['verdict'] == 'allow' and benign['rule_id'] == '0001'

            banned = requests.get(base + '/index.html', headers={'X-Forwarded-For': '10.0.0.6'}, timeout=5).json()
            assert banned['verdict'] == 'block' and banned['rule_id'] == '0003'      # banned IP via XFF

            # POST captured (harness) — deterministic
            captured = {'request_id': 'sn-x', 'method': 'GET', 'path': '/wp-login.php', 'host': 'h',
                        'source_ip': '1.2.3.4', 'user_agent': 'c', 'querystring': '', 'aws_request_id': '',
                        'received_at': '2026-01-01T00:00:00Z', 'cache_status': 'miss'}
            posted = requests.post(base + '/', data=json.dumps(captured), timeout=5).json()
            assert posted['verdict'] == 'block' and posted['rule_id'] == '0018'
            assert posted['request_id'] == 'sn-x'                                    # captured used verbatim
        finally:
            proc.terminate()
            shutil.rmtree(ctx, ignore_errors=True)
