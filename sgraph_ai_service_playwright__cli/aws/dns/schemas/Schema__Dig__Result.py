# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Dig__Result
# Result of one dig invocation against a single nameserver or resolver.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                 import Type_Safe


class Schema__Dig__Result(Type_Safe):
    nameserver  : str                                                                 # The nameserver or resolver that was queried
    name        : str                                                                 # The DNS name that was queried
    rtype       : str                                                                 # Record type queried (A, AAAA, CNAME, …)
    values      : list                                                                # Parsed lines from dig +short output
    exit_code   : int                                                                 # subprocess exit code (0 = success)
    error       : str                                                                 # Empty on success; stderr or exception message on failure
    duration_ms : int                                                                 # Wall-clock duration of the subprocess call in milliseconds
