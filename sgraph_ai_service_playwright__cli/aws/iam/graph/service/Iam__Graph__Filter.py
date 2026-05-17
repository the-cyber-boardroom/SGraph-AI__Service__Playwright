# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Iam__Graph__Filter
# Predicate functions for filtering IAM graph node lists.
# Three modes: unused (no recent activity), name-pattern glob, aws-default.
# ═══════════════════════════════════════════════════════════════════════════════

import fnmatch
from datetime import datetime, timezone

from osbot_utils.type_safe.Type_Safe                                                            import Type_Safe

from sgraph_ai_service_playwright__cli.aws.iam.graph.collections.List__Schema__IAM__Graph__Node import List__Schema__IAM__Graph__Node
from sgraph_ai_service_playwright__cli.aws.iam.graph.enums.Enum__IAM__Node__Type               import Enum__IAM__Node__Type
from sgraph_ai_service_playwright__cli.aws.iam.graph.schemas.Schema__IAM__Graph__Node          import Schema__IAM__Graph__Node


_STALE_DAYS_DEFAULT = 90


class Iam__Graph__Filter(Type_Safe):

    # ── public ────────────────────────────────────────────────────────────────

    def filter_unused(self,
                      nodes : List__Schema__IAM__Graph__Node,
                      days  : int = _STALE_DAYS_DEFAULT) -> List__Schema__IAM__Graph__Node:
        cutoff = datetime.now(tz=timezone.utc).timestamp() - days * 86400
        result = List__Schema__IAM__Graph__Node()
        for node in nodes:
            if node.node_type != Enum__IAM__Node__Type.ROLE:
                continue
            if not node.last_used:                                                # never used
                result.append(node)
                continue
            ts = self.parse_iso_ts(node.last_used)
            if ts is not None and ts < cutoff:
                result.append(node)
        return result

    def filter_pattern(self,
                       nodes   : List__Schema__IAM__Graph__Node,
                       pattern : str) -> List__Schema__IAM__Graph__Node:
        result = List__Schema__IAM__Graph__Node()
        for node in nodes:
            if fnmatch.fnmatch(node.name, pattern):
                result.append(node)
        return result

    def filter_aws_default(self,
                            nodes : List__Schema__IAM__Graph__Node) -> List__Schema__IAM__Graph__Node:
        result = List__Schema__IAM__Graph__Node()
        for node in nodes:
            if node.is_aws_default or node.is_service_linked:
                result.append(node)
        return result

    # ── internal ──────────────────────────────────────────────────────────────

    def parse_iso_ts(self, ts_str: str) -> float:
        if not ts_str:
            return None
        for fmt in ('%Y-%m-%dT%H:%M:%S+00:00',
                    '%Y-%m-%dT%H:%M:%S.%f+00:00',
                    '%Y-%m-%d %H:%M:%S+00:00',
                    '%Y-%m-%dT%H:%M:%SZ',
                    '%Y-%m-%dT%H:%M:%S'):
            try:
                dt = datetime.strptime(ts_str[:26], fmt[:len(fmt)])
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.timestamp()
            except ValueError:
                continue
        return None
