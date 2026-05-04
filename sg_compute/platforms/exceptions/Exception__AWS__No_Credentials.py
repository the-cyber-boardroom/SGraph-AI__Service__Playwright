# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Exception__AWS__No_Credentials
# Raised by any Platform method when AWS credentials are absent or invalid.
# Not EC2-specific — credentials problems apply to any AWS-backed platform.
# ═══════════════════════════════════════════════════════════════════════════════


class Exception__AWS__No_Credentials(Exception):
    pass
