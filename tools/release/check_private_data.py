"""Check publishable files/history for local credentials without printing values.

Uses local .env only as a private deny-list; it never emits credential contents.
This is a guardrail, not a substitute for a dedicated secret scanner/review.
"""
import argparse
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--history', action='store_true')
    args = parser.parse_args()
    values = set()
    env = ROOT / '.env'
    if env.exists():
        for line in env.read_text().splitlines():
            if '=' not in line or line.lstrip().startswith('#'):
                continue
            key, value = line.split('=', 1)
            value = value.strip().strip('\"\'')
            if len(value) >= 8 and re.search(r'KEY|TOKEN|SECRET|PASSWORD|USERNAME|LOGIN|EMAIL|CLIENT_ID|ACCOUNT_ID', key):
                values.add(value.encode())
    patterns = [
        re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
        re.compile(rb'gh[pousr]_[A-Za-z0-9]{30,}'),
        re.compile(rb'github_pat_[A-Za-z0-9_]{40,}'),
        re.compile(rb'AIza[A-Za-z0-9_-]{30,}'),
        re.compile(rb'GOCSPX-[A-Za-z0-9_-]{20,}'),
        re.compile(rb'sk-(?:proj-|ant-)?[A-Za-z0-9_-]{32,}'),
    ]
    forbidden = re.compile(r'(^|/)(\.env(?:\..*)?|harvey\.local\.yaml|auth\.json|credentials\.json|token\.json|linkedin_cookies\.json)$|\.(?:db|sqlite|sqlite3)(?:-wal|-shm)?$')
    findings = []
    files = sorted(set(git('ls-files', '-z', '--cached', '--others', '--exclude-standard').decode().split('\0')) - {''})
    checked = 0
    for name in files:
        path = ROOT / name
        if not path.is_file():
            continue
        checked += 1
        if forbidden.search(name) and name != '.env.example':
            findings.append({'file': name, 'reason': 'private file name'})
        data = path.read_bytes()
        if any(value in data for value in values):
            findings.append({'file': name, 'reason': 'matches local credential/account value'})
        if any(pattern.search(data) for pattern in patterns):
            findings.append({'file': name, 'reason': 'credential-like pattern'})
    history_blobs = 0
    if args.history:
        for line in git('rev-list', '--objects', '--all').decode().splitlines():
            oid, _, name = line.partition(' ')
            if git('cat-file', '-t', oid).strip() != b'blob':
                continue
            history_blobs += 1
            data = git('cat-file', 'blob', oid)
            if any(value in data for value in values) or any(p.search(data) for p in patterns):
                findings.append({'object': oid, 'file': name, 'reason': 'credential match in Git history'})
            if forbidden.search(name) and name != '.env.example':
                findings.append({'object': oid, 'file': name, 'reason': 'private file in Git history'})
    print(json.dumps({'files_checked': checked, 'history_blobs_checked': history_blobs, 'findings': findings}, indent=2))
    return bool(findings)

if __name__ == '__main__':
    raise SystemExit(main())
