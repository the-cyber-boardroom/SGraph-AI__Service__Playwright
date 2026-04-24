# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — AWS__Error__Translator
# Maps boto3 / botocore exceptions to a Schema__AWS__Error__Hint so the CLI
# can render a friendly message instead of a SigV4 stack trace. Pure logic —
# no Rich, no Typer, no I/O. Tests pass real exception instances; the elastic
# CLI wraps every command with it.
#
# Recognition is intentionally conservative: anything we don't classify comes
# back as `recognised=False` and the CLI re-raises so surprises are still
# loud and visible.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__AWS__Error__Hint     import Schema__AWS__Error__Hint


CLIENT_ERROR_HEADLINES = {                                                          # botocore ClientError 'Code' → user-facing copy
    'UnauthorizedOperation'  : ('denied'  , 'Your IAM principal is not allowed to perform this EC2 operation.',
                                ['Confirm the IAM user/role has a policy allowing ec2:RunInstances, ec2:DescribeInstances, ec2:CreateSecurityGroup, ec2:AuthorizeSecurityGroupIngress, ec2:TerminateInstances, ssm:GetParameter.',
                                 'Run: aws sts get-caller-identity to confirm which principal is in use.']) ,
    'AccessDenied'           : ('denied'  , 'AWS denied the request — the principal is missing a permission.',
                                ['Same fix as UnauthorizedOperation: attach an IAM policy allowing the EC2 + SSM actions used by sp elastic.']) ,
    'AccessDeniedException'  : ('denied'  , 'AWS denied the request — the principal is missing a permission.',
                                ['Same fix as UnauthorizedOperation: attach an IAM policy allowing the EC2 + SSM actions used by sp elastic.']) ,
    'AuthFailure'            : ('expired' , 'AWS rejected the credentials. They are likely expired or revoked.',
                                ['If using SSO: refresh with: aws sso login.',
                                 'If using temporary keys: regenerate them.',
                                 'Run: aws sts get-caller-identity to verify which credentials are active.']) ,
    'ExpiredToken'           : ('expired' , 'Your AWS session token has expired.',
                                ['Refresh: aws sso login, or regenerate STS credentials.']) ,
    'ExpiredTokenException'  : ('expired' , 'Your AWS session token has expired.',
                                ['Refresh: aws sso login, or regenerate STS credentials.']) ,
    'RequestExpired'         : ('clock'   , 'AWS rejected the request as expired — likely a clock-skew issue.',
                                ['Sync the local clock (e.g. sudo timedatectl set-ntp true on Linux, or w32tm /resync on Windows).']) ,
    'SignatureDoesNotMatch'  : ('expired' , 'AWS rejected the request signature. Credentials may be stale or for the wrong account.',
                                ['Re-export credentials, or run: aws sts get-caller-identity to confirm the active account.']) ,
    'OptInRequired'          : ('region'  , 'The AWS region is not enabled for this account.',
                                ['Enable the region in AWS Console → Account → AWS Regions, or pass --region <enabled-region>.']) ,
    'UnauthorizedAccess'     : ('region'  , 'The AWS region is not enabled for this account.',
                                ['Enable the region in AWS Console, or pass --region <enabled-region>.']) ,
    'InvalidClientTokenId'   : ('no-credentials', 'AWS does not recognise the access key id.',
                                ['Double-check AWS_ACCESS_KEY_ID (and AWS_PROFILE if set).',
                                 'Run: aws sts get-caller-identity to verify the key.']) ,
}


class AWS__Error__Translator(Type_Safe):                                            # Pure mapper

    def translate(self, exc: BaseException) -> Schema__AWS__Error__Hint:
        name = type(exc).__name__

        if name == 'NoCredentialsError':                                            # botocore.exceptions.NoCredentialsError
            return Schema__AWS__Error__Hint(
                recognised = True                                                              ,
                category   = 'no-credentials'                                                  ,
                headline   = 'AWS credentials not found.'                                      ,
                body       = 'sp elastic needs AWS credentials to talk to EC2 + SSM, but boto3 could not locate any.',
                hints      = ['Run: aws configure (writes ~/.aws/credentials),'                ,
                              'or export AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY (+ AWS_SESSION_TOKEN if using STS),',
                              'or set AWS_PROFILE=<name> to pick a profile from ~/.aws/credentials.'])

        if name in ('EndpointConnectionError', 'ConnectionClosedError', 'ConnectTimeoutError', 'ReadTimeoutError'):
            return Schema__AWS__Error__Hint(
                recognised = True                                                              ,
                category   = 'network'                                                         ,
                headline   = 'Cannot reach AWS.'                                               ,
                body       = 'boto3 could not connect to the AWS endpoint.'                    ,
                hints      = ['Check internet / VPN / corporate proxy.'                        ,
                              'Pass --region if the default region is wrong or unreachable.'  ,
                              'For VPC-only environments, confirm AWS interface endpoints are present for ec2 + ssm.'])

        if name == 'NoRegionError':
            return Schema__AWS__Error__Hint(
                recognised = True                                                              ,
                category   = 'region'                                                          ,
                headline   = 'No AWS region configured.'                                       ,
                body       = 'boto3 has no default region and --region was not passed.'        ,
                hints      = ['Pass --region <code> (e.g. eu-west-2),'                         ,
                              'or set AWS_DEFAULT_REGION / AWS_REGION,'                        ,
                              'or run: aws configure set region <code>.'])

        if name == 'ClientError':
            response = getattr(exc, 'response', None) or {}
            error    = response.get('Error', {}) if isinstance(response, dict) else {}
            code     = str(error.get('Code', ''))
            message  = str(error.get('Message', ''))
            if code in CLIENT_ERROR_HEADLINES:
                category, headline, hints = CLIENT_ERROR_HEADLINES[code]
                body = message or f'AWS returned {code}.'
                return Schema__AWS__Error__Hint(recognised = True              ,
                                                category   = category          ,
                                                headline   = headline           ,
                                                body       = body              ,
                                                hints      = list(hints)       )

        return Schema__AWS__Error__Hint(recognised = False, category = 'unknown')
