# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Sentinel__Rule__Registry
# Metadata for the six MVP rules (ids, names, MITRE tags, confidence, action).
# Rule *logic* lives in runtime/layer1/sentinel_l1.js — this is the Python-side
# description used by `sg sentinel rules list/show`. Order mirrors the engine's
# first-block-wins evaluation order (0001 capture-all is the implicit allow tail).
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                       import Type_Safe

from sgraph_ai_service_playwright__cli.sentinel.collections.List__Schema__Sentinel__Rule   import List__Schema__Sentinel__Rule
from sgraph_ai_service_playwright__cli.sentinel.enums.Enum__Sentinel__Action               import Enum__Sentinel__Action
from sgraph_ai_service_playwright__cli.sentinel.enums.Enum__Sentinel__Layer                import Enum__Sentinel__Layer
from sgraph_ai_service_playwright__cli.sentinel.schemas.Schema__Sentinel__Rule             import Schema__Sentinel__Rule

_CONFIDENCE = 'deterministic-certain'


class Sentinel__Rule__Registry(Type_Safe):

    def all(self) -> List__Schema__Sentinel__Rule:
        rules = List__Schema__Sentinel__Rule()
        rules.append(Schema__Sentinel__Rule(rule_id='0001', name='capture-all',      layer=Enum__Sentinel__Layer.L1,
                                            attack_tag='',       confidence=_CONFIDENCE, action=Enum__Sentinel__Action.PASS,
                                            description='Assembles the log fields for every request; pure observation.'))
        rules.append(Schema__Sentinel__Rule(rule_id='0003', name='banned-ip',        layer=Enum__Sentinel__Layer.L1,
                                            attack_tag='T1595',  confidence=_CONFIDENCE, action=Enum__Sentinel__Action.DROP_403,
                                            description='Source IP present in the embedded ban list.'))
        rules.append(Schema__Sentinel__Rule(rule_id='0007', name='malformed-request', layer=Enum__Sentinel__Layer.L1,
                                            attack_tag='T1190',  confidence=_CONFIDENCE, action=Enum__Sentinel__Action.DROP_403,
                                            description='Structurally invalid request (missing method/path or path not rooted at /).'))
        rules.append(Schema__Sentinel__Rule(rule_id='0012', name='path-never-valid',  layer=Enum__Sentinel__Layer.L1,
                                            attack_tag='T1190',  confidence=_CONFIDENCE, action=Enum__Sentinel__Action.DROP_403,
                                            description='Path that is never valid on this site, e.g. /etc/passwd or .. traversal.'))
        rules.append(Schema__Sentinel__Rule(rule_id='0014', name='hidden-file-probe', layer=Enum__Sentinel__Layer.L1,
                                            attack_tag='T1083',  confidence=_CONFIDENCE, action=Enum__Sentinel__Action.DEFLECT_404,
                                            description='Probe for hidden files such as /.env or /.git/.'))
        rules.append(Schema__Sentinel__Rule(rule_id='0018', name='wp-scan-on-static', layer=Enum__Sentinel__Layer.L1,
                                            attack_tag='T1595',  confidence=_CONFIDENCE, action=Enum__Sentinel__Action.DEFLECT_404,
                                            description='WordPress scan (/wp-login.php, /wp-admin/, /xmlrpc.php) on a static site.'))
        return rules

    def get(self, needle: str) -> Schema__Sentinel__Rule:                           # match by rule id OR name; None when no such rule
        key = str(needle).strip().lower()
        for rule in self.all():
            if key in (str(rule.rule_id).lower(), str(rule.name).lower()):
                return rule
        return None
