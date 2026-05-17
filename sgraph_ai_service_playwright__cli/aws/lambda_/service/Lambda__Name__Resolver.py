# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Lambda__Name__Resolver
# 5-tier fuzzy resolver for Lambda function names.
#
# Tier 1: Exact match (score 1000)
# Tier 2: Case-insensitive exact (score 900)
# Tier 3: Starts-with prefix, case-insensitive (score 800 - mismatch pos)
# Tier 4: Substring match, case-insensitive (score 600 - match position)
# Tier 5: Subsequence match (score 400 - name length)
#
# Clear winner: top score must exceed second by >= 10 points.
# Cache: function list cached for cache_ttl_seconds (default 300s).
# ═══════════════════════════════════════════════════════════════════════════════

import time

from osbot_utils.type_safe.Type_Safe                                             import Type_Safe

from sgraph_ai_service_playwright__cli.aws.lambda_.service.Lambda__AWS__Client  import Lambda__AWS__Client


class Lambda__Name__Resolver(Type_Safe):
    cache_ttl_seconds : int   = 300
    aws_client        : Lambda__AWS__Client = None

    _cache_names      : list  = None    # cached list of function name strings
    _cache_expires_at : float = 0.0     # epoch seconds when cache expires

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.aws_client is None:
            self.aws_client = Lambda__AWS__Client()

    # ── public ────────────────────────────────────────────────────────────────

    def resolve(self, query: str, exact: bool = False) -> str:
        names = self.all_function_names()
        if exact:
            if query in names:
                return query
            raise ValueError(f'Function not found (exact): {query!r}')
        matches = self._rank(query, names)
        if not matches:
            closest = self._closest(query, names, n=3)
            hint    = ', '.join(closest) if closest else 'none'
            raise ValueError(
                f'No function matching {query!r}. Closest: {hint}'
            )
        if len(matches) == 1:
            if matches[0][1] < 800:                                               # warn on subsequence tier
                pass                                                              # caller may print warning
            return matches[0][0]
        best_name, best_score = matches[0]
        if len(matches) > 1:
            _, second_score = matches[1]
            if best_score > second_score + 10:                                    # clear winner
                return best_name
        candidates = ', '.join(n for n, _ in matches[:8])
        raise ValueError(
            f'Ambiguous function name {query!r} — {len(matches)} matches: {candidates}. '
            f'Add more characters to disambiguate.'
        )

    def all_function_names(self) -> list:
        now = time.time()
        if self._cache_names is not None and now < self._cache_expires_at:
            return self._cache_names
        fns = self.aws_client.list_functions()
        self._cache_names      = [str(f.name) for f in fns]
        self._cache_expires_at = now + self.cache_ttl_seconds
        return self._cache_names

    def invalidate_cache(self):
        self._cache_names      = None
        self._cache_expires_at = 0.0

    # ── scoring ───────────────────────────────────────────────────────────────

    def _rank(self, query: str, names: list) -> list:
        q_lower = query.lower()
        scored  = []
        for name in names:
            n_lower = name.lower()
            score   = self._score(query, q_lower, name, n_lower)
            if score > 0:
                scored.append((name, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def _score(self, query: str, q_lower: str, name: str, n_lower: str) -> int:
        if name == query:                                                          # tier 1: exact
            return 1000
        if n_lower == q_lower:                                                    # tier 2: case-insensitive exact
            return 900
        if n_lower.startswith(q_lower):                                           # tier 3: prefix
            return 800 - len(q_lower)
        pos = n_lower.find(q_lower)
        if pos >= 0:                                                              # tier 4: substring
            return 600 - pos
        if self._is_subsequence(q_lower, n_lower):                               # tier 5: subsequence
            return 400 - len(name)
        return 0

    def _is_subsequence(self, query: str, name: str) -> bool:
        qi = 0
        for ch in name:
            if qi < len(query) and ch == query[qi]:
                qi += 1
        return qi == len(query)

    def _closest(self, query: str, names: list, n: int = 3) -> list:
        def edit_dist(a: str, b: str) -> int:
            if len(a) > len(b):
                a, b = b, a
            row = list(range(len(a) + 1))
            for c2 in b:
                new = [row[0] + 1]
                for j, c1 in enumerate(a):
                    new.append(min(new[-1] + 1, row[j + 1] + 1, row[j] + (c1 != c2)))
                row = new
            return row[-1]
        ranked = sorted(names, key=lambda nm: edit_dist(query.lower(), nm.lower()))
        return ranked[:n]
