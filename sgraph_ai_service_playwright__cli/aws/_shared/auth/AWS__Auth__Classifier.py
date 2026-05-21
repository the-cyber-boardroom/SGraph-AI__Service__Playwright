# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — aws shared auth: AWS__Auth__Classifier
# Decides whether an exception is an AWS *auth* failure (missing/expired/insufficient
# credentials) — the errors the guard should turn into a helpful menu rather than a
# traceback. Generic across every sg aws client. Pure functions — no AWS calls.
# ═══════════════════════════════════════════════════════════════════════════════

_AUTH_CLIENT_CODES = {                                                               # botocore ClientError codes that mean "auth problem"
    'AccessDenied', 'AccessDeniedException', 'UnauthorizedOperation',
    'ExpiredToken', 'ExpiredTokenException', 'RequestExpired',
    'InvalidClientTokenId', 'UnrecognizedClientException',
    'AuthFailure', 'InvalidAccessKeyId', 'SignatureDoesNotMatch',
    'InvalidUserID.NotFound', 'TokenRefreshRequired',
}

_AUTH_EXC_NAMES = {                                                                  # botocore exception class names (avoid hard import)
    'NoCredentialsError', 'PartialCredentialsError', 'CredentialRetrievalError',
    'NoAuthTokenError', 'TokenRetrievalError', 'UnauthorizedSSOTokenError',
    'SSOTokenLoadError',
}


def _client_error_code(exc) -> str:
    response = getattr(exc, 'response', None)
    if isinstance(response, dict):
        return response.get('Error', {}).get('Code', '') or ''
    return ''


def is_auth_error(exc : BaseException) -> bool:
    if type(exc).__name__ in _AUTH_EXC_NAMES:
        return True
    code = _client_error_code(exc)
    return bool(code) and code in _AUTH_CLIENT_CODES


def auth_error_cause(exc : BaseException) -> str:                                    # short, human cause line
    name = type(exc).__name__
    code = _client_error_code(exc)
    if code:
        return f'{code}: {exc}'.strip()
    return f'{name}: {exc}'.strip()
