"""Generate local operator config without ever printing a Meta key."""
from pathlib import Path
import secrets
ROOT=Path(__file__).resolve().parents[1]
path=ROOT/'.env'
if path.exists():
    print('.env already exists; preserved. Use its REPROPATCH_AUTH_TOKEN to sign in.')
else:
    token=secrets.token_urlsafe(32)
    content=(ROOT/'.env.example').read_text().replace('REPROPATCH_AUTH_TOKEN=','REPROPATCH_AUTH_TOKEN='+token,1)
    content=content.replace('REPROPATCH_ACCEPTANCE_KEY=', 'REPROPATCH_ACCEPTANCE_KEY='+secrets.token_urlsafe(32),1)
    path.write_text(content);path.chmod(0o600)
    print('Local .env created. Operator token (not a Meta API key):')
    print(token)
print('Next: bash scripts/start_local.sh')
