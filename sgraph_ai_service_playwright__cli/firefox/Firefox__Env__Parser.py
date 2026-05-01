# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Firefox__Env__Parser
# Pure helper: parse SP_FIREFOX_PASSWORD from .env file content.
# No AWS, no typer — importable from tests without side-effects.
# ═══════════════════════════════════════════════════════════════════════════════


def extract_password_from_env(content: str) -> tuple:
    """Return (password, stripped_content).

    Recognises SP_FIREFOX_PASSWORD=<value> (with or without quotes).
    That line is removed from the content sent to the instance — mitmproxy
    doesn't need it; the password travels via docker-compose env instead.
    """
    password   = ''
    kept_lines = []
    for line in content.splitlines(keepends=True):
        stripped = line.strip()
        if stripped.startswith('SP_FIREFOX_PASSWORD='):
            value = stripped[len('SP_FIREFOX_PASSWORD='):]
            if len(value) >= 2 and value[0] in ('"', "'") and value[-1] == value[0]:
                value = value[1:-1]                                                 # strip surrounding quotes
            password = value
        else:
            kept_lines.append(line)
    return password, ''.join(kept_lines)
