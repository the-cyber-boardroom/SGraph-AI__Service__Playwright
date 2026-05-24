# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Sentinel__Traffic__Corpus
# The use-case traffic corpus: a labelled mix of valid + invalid requests with the
# verdict/rule we expect SG/Sentinel to produce. Covers every MVP rule plus benign
# variety, so a run exercises the rules AND measures impact. Banned IP fixture
# (10.0.0.6) matches rules.embedded.json.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.sentinel.enums.Enum__Sentinel__Verdict             import Enum__Sentinel__Verdict
from sgraph_ai_service_playwright__cli.sentinel.traffic.enums.Enum__Traffic__Category     import Enum__Traffic__Category
from sgraph_ai_service_playwright__cli.sentinel.traffic.schemas.List__Schema__Traffic__Case import List__Schema__Traffic__Case
from sgraph_ai_service_playwright__cli.sentinel.traffic.schemas.Schema__Traffic__Case      import Schema__Traffic__Case

BENIGN    = Enum__Traffic__Category.BENIGN
MALICIOUS = Enum__Traffic__Category.MALICIOUS
MALFORMED = Enum__Traffic__Category.MALFORMED
ALLOW     = Enum__Sentinel__Verdict.ALLOW
BLOCK     = Enum__Sentinel__Verdict.BLOCK

# (name, method, path, ip, category, expected_verdict, expected_rule)
_CASES = [
    ('home',            'GET', '/',                  '198.51.100.2', BENIGN,    ALLOW, '0001'),
    ('index',           'GET', '/index.html',        '198.51.100.3', BENIGN,    ALLOW, '0001'),
    ('static-css',      'GET', '/static/style.css',  '198.51.100.4', BENIGN,    ALLOW, '0001'),
    ('static-js',       'GET', '/assets/app.js',     '198.51.100.5', BENIGN,    ALLOW, '0001'),
    ('api-read',        'GET', '/api/v1/items?id=7', '198.51.100.6', BENIGN,    ALLOW, '0001'),
    ('favicon',         'GET', '/favicon.ico',       '198.51.100.7', BENIGN,    ALLOW, '0001'),
    ('etc-passwd',      'GET', '/etc/passwd',        '185.10.10.10', MALICIOUS, BLOCK, '0012'),
    ('path-traversal',  'GET', '/../../etc/shadow',  '185.10.10.11', MALICIOUS, BLOCK, '0012'),
    ('dot-env',         'GET', '/.env',              '77.30.30.30',  MALICIOUS, BLOCK, '0014'),
    ('git-config',      'GET', '/.git/config',       '77.30.30.31',  MALICIOUS, BLOCK, '0014'),
    ('wp-login',        'GET', '/wp-login.php',      '91.20.20.20',  MALICIOUS, BLOCK, '0018'),
    ('wp-admin',        'GET', '/wp-admin/',         '91.20.20.21',  MALICIOUS, BLOCK, '0018'),
    ('xmlrpc',          'GET', '/xmlrpc.php',        '91.20.20.22',  MALICIOUS, BLOCK, '0018'),
    ('banned-ip',       'GET', '/index.html',        '10.0.0.6',     MALICIOUS, BLOCK, '0003'),
    ('malformed-empty', 'GET', '',                   '203.0.113.5',  MALFORMED, BLOCK, '0007'),
    ('malformed-rel',   'GET', 'noslash',            '203.0.113.6',  MALFORMED, BLOCK, '0007'),
]


class Sentinel__Traffic__Corpus(Type_Safe):

    def cases(self) -> List__Schema__Traffic__Case:
        out = List__Schema__Traffic__Case()
        for name, method, path, ip, category, verdict, rule in _CASES:
            out.append(Schema__Traffic__Case(name=name, method=method, path=path, source_ip=ip,
                                             category=category, expected_verdict=verdict, expected_rule=rule))
        return out
