# ═══════════════════════════════════════════════════════════════════════════════
# SG Credentials — Cli__Credentials
# Typer subapp for: sg credentials.*
#
# Commands
# ────────
#   sg credentials list
#   sg credentials add    <role> <access-key> <secret-key> [--region X] [--arn X]
#   sg credentials remove <role>
#   sg credentials switch <role>
#   sg credentials show   <role>
#   sg credentials status
#   sg credentials log    [--n 20]
#   sg credentials trace  <command...>   (dry-run resolver)
#   sg credentials export <role>
#   sg credentials init                  (interactive first-time wizard)
#   sg credentials set    <role>         (non-interactive role config)
#   sg credentials delete <role>         (alias for remove, with --yes flag)
#   sg credentials test   [role]         (STS GetCallerIdentity)
#   sg credentials whoami                (show active role)
#   sg credentials route  <command...>   (brief resolver — matched role only)
#   sg credentials wipe                  (delete ALL sg.* entries)
#   sg credentials backup --to <path>
#   sg credentials restore --from <path>
#   sg credentials edit                  (open in $EDITOR)
# ═══════════════════════════════════════════════════════════════════════════════

import json
import os

import typer
from typing import List, Optional

from sgraph_ai_service_playwright__cli.credentials.enums.Enum__Audit__Action                  import Enum__Audit__Action
from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__AWS__Region            import Safe_Str__AWS__Region
from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__AWS__Role__ARN         import Safe_Str__AWS__Role__ARN
from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__AWS__Account_Id        import Safe_Str__AWS__Account_Id
from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__Role__Name             import Safe_Str__Role__Name
from sgraph_ai_service_playwright__cli.credentials.schemas.Schema__AWS__Role__Config           import Schema__AWS__Role__Config
from sgraph_ai_service_playwright__cli.credentials.service.Audit__Log                         import Audit__Log
from sgraph_ai_service_playwright__cli.credentials.service.Credentials__Resolver              import Credentials__Resolver
from sgraph_ai_service_playwright__cli.credentials.service.Credentials__Store                 import Credentials__Store
from sgraph_ai_service_playwright__cli.osx.keyring.service.Keyring__Mac__OS                   import Keyring__Mac__OS


_CURRENT_ROLE_ENV = 'SG_CREDENTIALS__CURRENT_ROLE'


app = typer.Typer(no_args_is_help=True,
                  help='Manage AWS credentials and roles stored in the macOS Keychain.')


def _store() -> Credentials__Store:
    return Credentials__Store(keyring=Keyring__Mac__OS())


def _audit() -> Audit__Log:
    return Audit__Log()


# ═══════════════════════════════════════════════════════════════════════════════
# existing commands (v0.2.25)
# ═══════════════════════════════════════════════════════════════════════════════

@app.command(name='list')
def list_cmd():
    """List all registered roles."""
    store = _store()
    roles = store.role_list()
    if not roles:
        typer.echo('(no roles configured)')
        return
    current = os.environ.get(_CURRENT_ROLE_ENV, '')
    for role in roles:
        marker = ' *' if role == current else ''
        typer.echo(f'  {role}{marker}')
    _audit().log(Enum__Audit__Action.LIST, command_args='list roles')


@app.command()
def add(role       : str  = typer.Argument(..., help='Role name (e.g. admin, dev).'),
        access_key : str  = typer.Argument(..., help='AWS access key ID.'),
        secret_key : str  = typer.Argument(..., help='AWS secret access key.'),
        region     : str  = typer.Option('us-east-1', help='Default AWS region.'),
        arn        : str  = typer.Option('', help='STS AssumeRole ARN (leave empty to use keys directly).'),
        account_id : str  = typer.Option('', '--account-id', help='AWS account ID (12 digits). Auto-detected via STS if omitted.'),
        detect     : bool = typer.Option(True,  '--detect/--no-detect', help='Auto-detect account ID via STS GetCallerIdentity when --account-id is not given.')):
    """Add or update credentials for a role."""
    store  = _store()
    ok_aws = store.aws_credentials_set(role, access_key, secret_key)
    if not ok_aws:
        typer.echo(f'[error] failed to save AWS credentials for {role!r}', err=True)
        raise typer.Exit(1)

    if not account_id and detect:
        account_id = _detect_account_id(store, role, region, arn) or ''
        if account_id:
            typer.echo(f'[detected] account_id: {account_id}')
        else:
            typer.echo('[warn] could not auto-detect account_id; saving without it', err=True)

    config = Schema__AWS__Role__Config(
        name            = Safe_Str__Role__Name      (role)       ,
        region          = Safe_Str__AWS__Region     (region)     ,
        assume_role_arn = Safe_Str__AWS__Role__ARN  (arn)        ,
        session_name    = Safe_Str__Role__Name      (f'sg-{role}'),
        account_id      = Safe_Str__AWS__Account_Id (account_id) ,
    )
    ok_cfg = store.role_set(config)
    if ok_cfg:
        typer.echo(f'[ok] role {role!r} added/updated')
        _audit().log(Enum__Audit__Action.ADD, role=role, command_args=f'credentials add {role} <redacted> <redacted>')
    else:
        typer.echo(f'[error] failed to save role config for {role!r}', err=True)
        raise typer.Exit(1)


def _detect_account_id(store, role: str, region: str, arn: str) -> str:
    """Call STS GetCallerIdentity to populate account_id. Returns '' on failure."""
    from sgraph_ai_service_playwright__cli.credentials.service.Sg__Aws__Session import Sg__Aws__Session

    placeholder = Schema__AWS__Role__Config(
        name            = Safe_Str__Role__Name      (role)       ,
        region          = Safe_Str__AWS__Region     (region)     ,
        assume_role_arn = Safe_Str__AWS__Role__ARN  (arn)        ,
        session_name    = Safe_Str__Role__Name      (f'sg-{role}'),
    )
    store.role_set(placeholder)

    session = Sg__Aws__Session(store=store)
    sts     = session.boto3_client(role, 'sts')
    if sts is None:
        return ''
    try:
        return str(sts.get_caller_identity().get('Account', ''))
    except Exception:
        return ''


@app.command()
def remove(role: str = typer.Argument(..., help='Role name to remove.')):
    """Remove all credentials for a role."""
    store = _store()
    ok    = store.role_delete(role)
    if ok:
        typer.echo(f'[ok] role {role!r} removed')
        _audit().log(Enum__Audit__Action.REMOVE, role=role, command_args=f'credentials remove {role}')
    else:
        typer.echo(f'[not found] role {role!r}', err=True)
        raise typer.Exit(1)


@app.command()
def switch(role: str = typer.Argument(..., help='Role name to activate for this shell session.')):
    """Print the shell command to activate a role (eval the output)."""
    store = _store()
    creds = store.aws_credentials_get(role)
    if creds is None:
        typer.echo(f'[error] role {role!r} not found', err=True)
        raise typer.Exit(1)
    config = store.role_get(role)
    region = str(config.region) if config else 'us-east-1'
    typer.echo(f'export AWS_ACCESS_KEY_ID={str(creds.access_key)!r}')
    typer.echo(f'export AWS_SECRET_ACCESS_KEY={str(creds.secret_key)!r}')
    typer.echo(f'export AWS_DEFAULT_REGION={region!r}')
    typer.echo(f'export {_CURRENT_ROLE_ENV}={role!r}')
    _audit().log(Enum__Audit__Action.SWITCH, role=role, command_args=f'credentials switch {role}')


@app.command()
def show(role: str = typer.Argument(..., help='Role name to inspect.')):
    """Show config for a role (secrets redacted)."""
    store  = _store()
    config = store.role_get(role)
    if config is None:
        typer.echo(f'[not found] role {role!r}', err=True)
        raise typer.Exit(1)
    creds  = store.aws_credentials_get(role)
    typer.echo(f'role          : {config.name}')
    typer.echo(f'region        : {config.region}')
    typer.echo(f'account_id    : {config.account_id or "(not set — run: sg credentials test " + role + ")"}')
    typer.echo(f'assume_role   : {config.assume_role_arn or "(direct)"}')
    typer.echo(f'session_name  : {config.session_name}')
    if creds is not None:
        typer.echo(f'access_key    : {str(creds.access_key)[:8]}…  (redacted)')
        typer.echo(f'secret_key    : ****  (redacted)')
    else:
        typer.echo('access_key    : (not set)')
        typer.echo('secret_key    : (not set)')
    _audit().log(Enum__Audit__Action.SHOW, role=role, command_args=f'credentials show {role}')


@app.command()
def status():
    """Show the currently active role."""
    current = os.environ.get(_CURRENT_ROLE_ENV, '')
    if current:
        typer.echo(f'active role: {current}')
    else:
        typer.echo('no role active  (use: eval $(sg credentials switch <role>))')
    _audit().log(Enum__Audit__Action.STATUS, command_args='credentials status')


@app.command()
def log(n: int = typer.Option(20, help='Number of recent audit events to show.')):
    """Show recent audit log entries."""
    audit  = _audit()
    events = audit.tail(n)
    if not events:
        typer.echo('(audit log is empty)')
        return
    for event in events:
        typer.echo(f"{event.get('timestamp','')}  {event.get('action',''):8}  {event.get('role',''):12}  {event.get('command_args','')}")


@app.command()
def trace(command: List[str] = typer.Argument(None, help='Command path to trace, e.g. aws lambda waker info')):
    """Dry-run: show which role would handle this command path. No AWS calls."""
    command_path = list(command) if command else []
    store    = _store()
    resolver = Credentials__Resolver(store=store)
    result   = resolver.trace(command_path)
    typer.echo(f'[trace] command path:    {" ".join(result.command_path) or "(empty)"}')
    typer.echo(f'[trace] routing match:   {result.matched_route or "(no match)"}  →  role: {result.matched_role or "(none)"}')
    chain_str = ' → '.join(result.role_chain)
    typer.echo(f'[trace] role chain:      {chain_str or "(empty)"}')
    typer.echo(f'[trace] would assume:    {result.would_assume_arn or "(direct creds — no assume)"}')
    typer.echo(f'[trace] session name:    {result.session_name_tmpl or "(n/a)"} (dry-run; not generated)')
    typer.echo(f'[trace] effective creds: source={result.source_creds}')


@app.command()
def export(role: str = typer.Argument(..., help='Role to export as shell environment variables.')):
    """Export credentials as shell env-var assignments (no keyring service names exposed)."""
    store  = _store()
    creds  = store.aws_credentials_get(role)
    config = store.role_get(role)
    if creds is None:
        typer.echo(f'[error] no credentials for role {role!r}', err=True)
        raise typer.Exit(1)
    region = str(config.region) if config else 'us-east-1'
    typer.echo(f'# credentials export for role: {role}')
    typer.echo(f'export AWS_ACCESS_KEY_ID={str(creds.access_key)!r}')
    typer.echo(f'export AWS_SECRET_ACCESS_KEY={str(creds.secret_key)!r}')
    typer.echo(f'export AWS_DEFAULT_REGION={region!r}')
    _audit().log(Enum__Audit__Action.EXPORT, role=role, command_args=f'credentials export {role}')


# ═══════════════════════════════════════════════════════════════════════════════
# new commands (v0.2.28 Phase C)
# ═══════════════════════════════════════════════════════════════════════════════

@app.command()
def init() -> None:
    """Interactive first-time wizard. Idempotent."""
    typer.echo('SG Credentials — first-time setup')
    store  = _store()
    role   = typer.prompt('Default role name', default='default')
    region = typer.prompt('AWS region',        default='us-east-1')
    existing = store.role_get(role)
    if existing is not None:
        overwrite = typer.confirm(f"Role '{role}' already exists. Overwrite?", default=False)
        if not overwrite:
            typer.echo('Aborted.')
            raise typer.Exit(0)
    access_key = typer.prompt('AWS Access Key ID',     hide_input=True)
    secret_key = typer.prompt('AWS Secret Access Key', hide_input=True)
    config = Schema__AWS__Role__Config(
        name            = Safe_Str__Role__Name(role)       ,
        region          = Safe_Str__AWS__Region(region)    ,
        assume_role_arn = Safe_Str__AWS__Role__ARN('')     ,
        session_name    = Safe_Str__Role__Name(f'sg-{role}'),
    )
    store.role_set(config)
    store.aws_credentials_set(role, access_key, secret_key)
    typer.echo(f"Role '{role}' configured for region '{region}'.")
    _audit().log(Enum__Audit__Action.ADD, role=role, command_args=f'credentials init {role}')


@app.command(name='set')
def set_role(role       : str = typer.Argument(...,                help='Role name.'          ),
             region     : str = typer.Option('us-east-1', '--region',     help='AWS region.'  ),
             access_key : str = typer.Option('',          '--access-key', help='Access key ID'),
             secret_key : str = typer.Option('',          '--secret-key', help='Secret key'   )) -> None:
    """Set or update a role's configuration."""
    store  = _store()
    config = Schema__AWS__Role__Config(
        name            = Safe_Str__Role__Name(role)       ,
        region          = Safe_Str__AWS__Region(region)    ,
        assume_role_arn = Safe_Str__AWS__Role__ARN('')     ,
        session_name    = Safe_Str__Role__Name(f'sg-{role}'),
    )
    store.role_set(config)
    if access_key and secret_key:
        store.aws_credentials_set(role, access_key, secret_key)
    typer.echo(f"Role '{role}' saved.")
    _audit().log(Enum__Audit__Action.ADD, role=role, command_args=f'credentials set {role}')


@app.command()
def delete(role: str = typer.Argument(..., help='Role name.'),
           yes : bool = typer.Option(False, '--yes', '-y',    help='Skip confirmation.')) -> None:
    """Delete a role and its AWS credentials."""
    if not yes:
        typer.confirm(f"Delete role '{role}' and its credentials?", abort=True)
    store = _store()
    ok    = store.role_delete(role)
    if ok:
        typer.echo(f'[ok] role {role!r} deleted')
        _audit().log(Enum__Audit__Action.REMOVE, role=role, command_args=f'credentials delete {role}')
    else:
        typer.echo(f'[not found] role {role!r}', err=True)
        raise typer.Exit(1)


@app.command(name='test')
def test_role(role: Optional[str] = typer.Argument(None, help='Role name (default: first configured).')) -> None:
    """Test AWS credentials by calling STS GetCallerIdentity."""
    from sgraph_ai_service_playwright__cli.credentials.service.Sg__Aws__Session import Sg__Aws__Session
    store = _store()
    if role is None:
        roles = store.role_list()
        if not roles:
            typer.echo('No roles configured.', err=True)
            raise typer.Exit(1)
        role = roles[0]
    session = Sg__Aws__Session(store=store)
    sts     = session.boto3_client(role, 'sts')
    if sts is None:
        typer.echo(f"Could not create STS client for role '{role}' — credentials missing or invalid.", err=True)
        raise typer.Exit(1)
    try:
        identity = sts.get_caller_identity()
        typer.echo(f"arn     : {identity.get('Arn','?')}")
        typer.echo(f"account : {identity.get('Account','?')}")
        typer.echo(f"user_id : {identity.get('UserId','?')}")
        _audit().log(Enum__Audit__Action.STATUS, role=role, success=True,
                     command_args=f'credentials test {role}')
    except Exception as e:
        typer.echo(f'STS call failed: {e}', err=True)
        _audit().log(Enum__Audit__Action.STATUS, role=role, success=False,
                     command_args=f'credentials test {role}', error=str(e))
        raise typer.Exit(1)


@app.command()
def whoami() -> None:
    """Print the currently active role (no AWS calls)."""
    from sgraph_ai_service_playwright__cli.credentials.service.Sg__Aws__Context import Sg__Aws__Context
    role = os.environ.get(_CURRENT_ROLE_ENV) or Sg__Aws__Context.get_current_role()
    if role:
        typer.echo(role)
        return
    store = _store()
    roles = store.role_list()
    if len(roles) == 1:
        typer.echo(f'{roles[0]}  (default — only role configured)')
    else:
        typer.echo('no active role  (use: as <role> in repl, or eval $(sg credentials switch <role>))')
    _audit().log(Enum__Audit__Action.STATUS, command_args='credentials whoami')


@app.command()
def route(command: List[str] = typer.Argument(..., help='Command words to resolve a role for.')) -> None:
    """Resolve which role handles a given command path (brief output)."""
    store    = _store()
    resolver = Credentials__Resolver(store=store)
    result   = resolver.trace(list(command))
    role     = result.matched_role
    if not role:
        roles = store.role_list()
        role  = roles[0] if roles else 'default'
    typer.echo(f'role: {role}  (route: {result.matched_route or "(no match)"})')
    _audit().log(Enum__Audit__Action.STATUS, command_args=f'credentials route {" ".join(command)}')


@app.command()
def wipe(yes_i_really_mean_it: bool = typer.Option(False, '--yes-i-really-mean-it',
                                                    help='Confirm deletion of ALL sg.* keyring entries.')) -> None:
    """Delete ALL sg.* keyring entries (irreversible)."""
    if not yes_i_really_mean_it:
        typer.echo('Use --yes-i-really-mean-it to confirm deletion of ALL sg.* keyring entries.')
        raise typer.Exit(1)
    store   = _store()
    entries = store.keyring.list(prefix='sg.')
    count   = 0
    for entry in entries:
        if store.keyring.delete(str(entry.service_name), str(entry.account)):
            count += 1
    typer.echo(f'Deleted {count} sg.* keyring entries.')
    _audit().log(Enum__Audit__Action.REMOVE,
                 command_args=f'credentials wipe --yes-i-really-mean-it ({count} entries)')


@app.command()
def backup(to: str = typer.Option(..., '--to', help='Output file path.')) -> None:
    """Backup all sg.* keyring entries to an encrypted file."""
    import base64
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives              import hashes
    from cryptography.fernet                         import Fernet
    passphrase = typer.prompt('Passphrase', hide_input=True, confirmation_prompt=True)
    store      = _store()
    entries    = store.keyring.list(prefix='sg.')
    records    = []
    for entry in entries:
        svc   = str(entry.service_name)
        acct  = str(entry.account)
        value = store.keyring.get(svc, acct)
        records.append({'service': svc, 'account': acct, 'value': value or ''})
    payload  = json.dumps(records).encode()
    salt     = os.urandom(16)
    kdf      = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=480000)
    key      = base64.urlsafe_b64encode(kdf.derive(passphrase.encode()))
    token    = Fernet(key).encrypt(payload)
    document = {'version': 'sg-backup-v1'                          ,
                'data'   : base64.b64encode(token).decode()        ,
                'salt'   : base64.b64encode(salt ).decode()        }
    try:
        with open(to, 'w') as f:
            json.dump(document, f)
        typer.echo(f'Backup written to {to} ({len(records)} entries).')
    except OSError as e:
        typer.echo(f'Failed to write backup: {e}', err=True)
        raise typer.Exit(1)


@app.command(name='restore')
def restore_backup(from_    : str  = typer.Option(...,   '--from',              help='Backup file path.'         ),
                   overwrite: bool = typer.Option(False, '--overwrite',          help='Overwrite existing entries.')) -> None:
    """Restore sg.* keyring entries from an encrypted backup."""
    import base64
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives              import hashes
    from cryptography.fernet                         import Fernet
    passphrase = typer.prompt('Passphrase', hide_input=True)
    try:
        with open(from_) as f:
            document = json.load(f)
    except (OSError, ValueError) as e:
        typer.echo(f'Failed to read backup: {e}', err=True)
        raise typer.Exit(1)
    if document.get('version') != 'sg-backup-v1':
        typer.echo('Unrecognised backup format.', err=True)
        raise typer.Exit(1)
    try:
        salt    = base64.b64decode(document['salt'])
        token   = base64.b64decode(document['data'])
        kdf     = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=480000)
        key     = base64.urlsafe_b64encode(kdf.derive(passphrase.encode()))
        payload = Fernet(key).decrypt(token)
        records = json.loads(payload)
    except Exception as e:
        typer.echo(f'Decryption failed: {e}', err=True)
        raise typer.Exit(1)
    store     = _store()
    conflicts = []
    for rec in records:
        if store.keyring.get(rec['service'], rec['account']) is not None:
            conflicts.append(f"{rec['service']}:{rec['account']}")
    if conflicts and not overwrite:
        typer.echo('Conflicts detected (use --overwrite to replace):')
        for c in conflicts:
            typer.echo(f'  {c}')
        raise typer.Exit(1)
    count = 0
    for rec in records:
        store.keyring.set(rec['service'], rec['account'], rec['value'])
        count += 1
    typer.echo(f'Restored {count} entries.')


@app.command()
def edit() -> None:
    """Open the credential store in an interactive editor."""
    from sgraph_ai_service_playwright__cli.credentials.edit.Credentials__Editor    import Credentials__Editor
    from sgraph_ai_service_playwright__cli.credentials.edit.Temp__File__Manager    import Temp__File__Manager
    from sgraph_ai_service_playwright__cli.credentials.edit.Edit__Session__Journal import Edit__Session__Journal
    from sgraph_ai_service_playwright__cli.credentials.edit.Editor__Launcher       import Editor__Launcher
    store  = _store()
    editor = Credentials__Editor(store           = store                   ,
                                  editor_launcher = Editor__Launcher()     ,
                                  journal         = Edit__Session__Journal(),
                                  temp_manager    = Temp__File__Manager()  )
    editor.run()
