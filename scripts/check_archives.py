"""Read-only digest guard for historical publication archives and figures."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
manifest = json.loads((ROOT / 'evidence/migration-audit.json').read_text())
count = 0
for item in manifest['files']:
    path = item['destination']
    if path.startswith(('downloads/', 'article/')):
        if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != item['sha256']:
            raise SystemExit(f'Historical evidence changed: {path}')
        count += 1
for archive in json.loads((ROOT / 'evidence/migration-audit.json').read_text())['archives']:
    with zipfile.ZipFile(ROOT / archive['path']) as z:
        for member in archive['members']:
            if hashlib.sha256(z.read(member['path'])).hexdigest() != member['sha256']:
                raise SystemExit(f"Archive member changed: {member['path']}")
print(f'Historical evidence verified: {count} files and all audited archive members')
