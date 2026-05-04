# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Elastic__HTTP__Client.elastic_probe
# Verifies the early-ES-ready signal: probe maps /_cluster/health responses
# onto Enum__Elastic__Probe__Status (UNREACHABLE / AUTH_REQUIRED / RED /
# YELLOW / GREEN). Subclasses request() instead of mocking — same pattern
# as test_bulk_post.py.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

import requests

from sgraph_ai_service_playwright__cli.elastic.enums.Enum__Elastic__Probe__Status   import Enum__Elastic__Probe__Status
from sgraph_ai_service_playwright__cli.elastic.service.Elastic__HTTP__Client        import Elastic__HTTP__Client


def build_response(status_code: int, body: bytes) -> requests.Response:
    response             = requests.Response()
    response.status_code = status_code
    response._content    = body
    return response


class Probing__Client(Elastic__HTTP__Client):                                       # Subclass that returns a canned response
    canned_status : int   = 200
    canned_body   : bytes = b''
    last_url      : str   = ''
    last_auth     : str   = ''                                                      # Captures the Authorization header so tests can confirm credentials were sent

    def request(self, method: str, url: str, *, headers: dict = None, data: bytes = None) -> requests.Response:
        self.last_url  = url
        self.last_auth = dict(headers or {}).get('Authorization', '')
        return build_response(self.canned_status, self.canned_body)


class Refusing__Client(Elastic__HTTP__Client):                                      # Raises a ConnectionError to mimic "nothing answering yet"
    def request(self, method: str, url: str, *, headers: dict = None, data: bytes = None) -> requests.Response:
        raise requests.ConnectionError('refused')


class test_elastic_probe(TestCase):

    def test_unreachable_when_request_raises(self):
        probe = Refusing__Client().elastic_probe('https://host', 'elastic', 'pw')
        assert probe == Enum__Elastic__Probe__Status.UNREACHABLE

    def test_unreachable_when_nginx_returns_502(self):                              # nginx is up, ES container still booting → 502 Bad Gateway from nginx
        client = Probing__Client(canned_status=502, canned_body=b'<html>502</html>')
        probe  = client.elastic_probe('https://host', 'elastic', 'pw')
        assert probe == Enum__Elastic__Probe__Status.UNREACHABLE

    def test_auth_required_on_401(self):
        client = Probing__Client(canned_status=401, canned_body=b'{"error":"unauthorized"}')
        probe  = client.elastic_probe('https://host', 'elastic', 'wrong')
        assert probe == Enum__Elastic__Probe__Status.AUTH_REQUIRED

    def test_auth_required_on_403(self):
        client = Probing__Client(canned_status=403, canned_body=b'{"error":"forbidden"}')
        probe  = client.elastic_probe('https://host', 'elastic', 'wrong')
        assert probe == Enum__Elastic__Probe__Status.AUTH_REQUIRED

    def test_green_status(self):
        client = Probing__Client(canned_status=200, canned_body=b'{"status":"green"}')
        probe  = client.elastic_probe('https://host', 'elastic', 'pw')
        assert probe == Enum__Elastic__Probe__Status.GREEN
        assert probe.is_ready() is True

    def test_yellow_status_is_ready_for_single_node(self):
        client = Probing__Client(canned_status=200, canned_body=b'{"status":"yellow"}')
        probe  = client.elastic_probe('https://host', 'elastic', 'pw')
        assert probe == Enum__Elastic__Probe__Status.YELLOW
        assert probe.is_ready() is True

    def test_red_status_is_not_ready(self):
        client = Probing__Client(canned_status=200, canned_body=b'{"status":"red"}')
        probe  = client.elastic_probe('https://host', 'elastic', 'pw')
        assert probe == Enum__Elastic__Probe__Status.RED
        assert probe.is_ready() is False

    def test_unknown_when_body_is_not_json(self):
        client = Probing__Client(canned_status=200, canned_body=b'not-json')
        probe  = client.elastic_probe('https://host', 'elastic', 'pw')
        assert probe == Enum__Elastic__Probe__Status.UNKNOWN

    def test_url_targets_cluster_health_via_nginx_rewrite(self):                    # /_elastic/* is the nginx prefix that strips and forwards to ES
        client = Probing__Client(canned_status=200, canned_body=b'{"status":"green"}')
        client.elastic_probe('https://host.example/', 'elastic', 'pw')
        assert client.last_url == 'https://host.example/_elastic/_cluster/health'

    def test_basic_auth_header_set_when_credentials_supplied(self):
        client = Probing__Client(canned_status=200, canned_body=b'{"status":"green"}')
        client.elastic_probe('https://host', 'elastic', 'pw')
        assert client.last_auth.startswith('Basic ')                                # base64('elastic:pw') — exact value matters less than that the header was set

    def test_no_auth_header_when_credentials_omitted(self):                         # Probe still works without creds — used in early boot before password is known
        client = Probing__Client(canned_status=200, canned_body=b'{"status":"green"}')
        client.elastic_probe('https://host')
        assert client.last_auth == ''
