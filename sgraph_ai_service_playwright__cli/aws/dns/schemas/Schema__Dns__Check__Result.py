# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Dns__Check__Result
# Aggregated result of a DNS check run (authoritative or public-resolver).
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                 import Type_Safe

from sgraph_ai_service_playwright__cli.aws.dns.enums.Enum__Dns__Check__Mode          import Enum__Dns__Check__Mode


class Schema__Dns__Check__Result(Type_Safe):
    mode         : Enum__Dns__Check__Mode                                             # AUTHORITATIVE | PUBLIC_RESOLVERS | LOCAL
    name         : str                                                                # The DNS name that was checked
    rtype        : str                                                                # Record type checked (A, CNAME, …)
    expected     : str                                                                # Expected value; empty = just check it resolves
    results      : list                                                               # List of Schema__Dig__Result objects (one per NS or resolver)
    passed       : bool                                                               # True when all (or quorum for public) agree on expected
    agreed_count : int                                                                # Number of nameservers/resolvers that returned the expected value
    total_count  : int                                                                # Total number of nameservers/resolvers queried
