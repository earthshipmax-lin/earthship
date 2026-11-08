#!/usr/bin/env python3
"""Portable, dependency-free, append-only project handoff snapshots (Python 3.10+, POSIX)."""
import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid

VERSION = '1.0.0'
DENIED = {'.git', '.aws', '.ssh', '.codex', 'node_modules', '__pycache__', '.venv', 'venv', 'dist', 'build', '.next', '.handoff-state'}
SECRET = re.compile(r'-----BEGIN (?:[A-Z ]+)?PRIVATE KEY-----|(?:gh[pousr]_|github_pat_|sk-(?:proj-)?)[A-Za-z0-9_-]{20,}|AKIA[A-Z0-9]{16}|(?i:(?:password|passwd|secret|api[_-]?key|access[_-]?token)\s*[=:]\s*[\"\x27]?)[A-Za-z0-9_+/=-]{16,}|https?://[^\s/:]+:[^\s/@]+@')
MAX_BYTES = 2 * 1024 * 1024

def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()

def git(root, *args, check=True):
    env = dict(os.environ, GIT_TERMINAL_PROMPT='0')
    p = subprocess.run(['git', '-C', str(root), *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, timeout=90)
    if check and p.returncode:
        # Error output can contain credentials in URLs: retain only a safe operation/code.
        raise RuntimeError(f'git {args[0]} failed (exit {p.returncode}); check connectivity, permissions or branch protection')
    return p

def atomic(path, value):
    tmp = path.with_name(path.name + '.tmp-' + uuid.uuid4().hex)
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    tmp.replace(path)

def allowed(path):
    p = Path(path)
    name = p.name.lower()
    return not (set(p.parts) & DENIED or name.startswith('.env') or
                any(x in name for x in ('credential', 'secret', 'id_rsa', 'id_ed25519')) or
                name.endswith(('.pem', '.key', '.p12', '.pfx', '.sqlite', '.db', '.log')))

def collect(repo):
    names = git(repo, 'ls-files', '-z', '--cached', '--others', '--exclude-standard').stdout.split(b'\0')
    files, omitted = {}, []
    for raw in sorted(set(names)):
        if not raw:
            continue
        name = os.fsdecode(raw)
        p = repo / name
        reason = None
        if not allowed(name):
            reason = 'excluded-path'
        elif p.is_symlink() or not p.resolve().is_relative_to(repo):
            reason = 'symlink-or-outside-root'
        elif not p.is_file():
            reason = 'not-a-regular-file'
        else:
            with p.open('rb') as f:
                data = f.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                reason = 'larger-than-2MiB'
            else:
                try:
                    text = data.decode('utf-8')
                    if '\0' in text:
                        reason = 'binary'
                    elif SECRET.search(text):
                        reason = 'possible-secret'
                    else:
                        files[name] = data
                except UnicodeDecodeError:
                    reason = 'binary'
        if reason:
            omitted.append({'path': name, 'reason': reason})
    return files, omitted

def initialize(args):
    repo = Path(args.repo).resolve()
    root = Path(git(repo, 'rev-parse', '--show-toplevel').stdout.decode().strip()).resolve()
    if repo != root:
        raise RuntimeError('--repo must name the Git root')
    remote = args.remote or git(repo, 'remote', 'get-url', 'origin').stdout.decode().strip()
    if not args.remote and not re.fullmatch(r'https://github\.com/[\w.-]+/[\w.-]+(?:\.git)?', remote):
        raise RuntimeError('origin must be a credential-free GitHub HTTPS URL')
    key = hashlib.sha256((str(repo) + remote).encode()).hexdigest()[:16]
    state = Path(args.state).resolve() if args.state else repo.parent / '.handoff-state' / key
    if state.is_relative_to(repo):
        raise RuntimeError('state directory must be outside project')
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    return repo, remote, state

def sync(args):
    repo, remote, state = initialize(args)
    with (state / 'sync.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        store = state / 'store'
        if not (store / '.git').exists():
            store.mkdir(exist_ok=True)
            git(store, 'init', '-b', 'agent-handoff')
            git(store, 'remote', 'add', 'origin', remote)
        git(store, 'config', 'user.name', 'Work Sync')
        git(store, 'config', 'user.email', 'work-sync@users.noreply.github.com')
        ident = state / 'session.json'
        if not ident.exists():
            atomic(ident, {'id': uuid.uuid4().hex})
        session = json.loads(ident.read_text())['id']
        # Commit locally before attempting network operations: outage must not lose work.
        files, omitted = collect(repo)
        head = git(repo, 'rev-parse', '--verify', 'HEAD', check=False)
        base = head.stdout.decode().strip() if head.returncode == 0 else None
        manifest = {'version': VERSION, 'source_commit': base, 'files': {n: hashlib.sha256(d).hexdigest() for n, d in files.items()}, 'omitted': omitted}
        digest = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
        marker = state / 'last-digest'
        if not marker.exists() or marker.read_text() != digest:
            snapshot = store / 'sessions' / session / (dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '-' + uuid.uuid4().hex[:8])
            snapshot.mkdir(parents=True)
            for name, data in files.items():
                target = snapshot / 'files' / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                target.chmod(0o755 if os.access(repo / name, os.X_OK) else 0o644)
            atomic(snapshot / 'manifest.json', dict(manifest, captured_at=now(), session=session))
            git(store, 'add', '--all')
            git(store, 'commit', '-m', 'handoff: checkpoint ' + now())
            marker.write_text(digest)
        last_error = None
        for attempt in range(3):
            try:
                refs = git(store, 'ls-remote', 'origin', 'refs/heads/agent-handoff').stdout.decode().split()
                if refs:
                    git(store, 'fetch', 'origin', 'refs/heads/agent-handoff')
                    # Unique paths allow independent machines to append without overwriting.
                    if git(store, 'merge-base', '--is-ancestor', 'FETCH_HEAD', 'HEAD', check=False).returncode == 0:
                        result = None
                    elif git(store, 'merge-base', 'HEAD', 'FETCH_HEAD', check=False).returncode == 0:
                        result = git(store, 'rebase', 'FETCH_HEAD', check=False)
                    else:
                        result = git(store, 'rebase', '--root', '--onto', 'FETCH_HEAD', check=False)
                    if result is not None and result.returncode:
                        git(store, 'rebase', '--abort', check=False)
                        raise RuntimeError('concurrent-history rebase failed; local queue preserved')
                git(store, 'push', 'origin', 'HEAD:refs/heads/agent-handoff')
                local = git(store, 'rev-parse', 'HEAD').stdout.decode().strip()
                remote_refs = git(store, 'ls-remote', 'origin', 'refs/heads/agent-handoff').stdout.decode().split()
                if not remote_refs:
                    raise RuntimeError('remote branch missing after push')
                remote_sha = remote_refs[0]
                if remote_sha != local:
                    git(store, 'fetch', 'origin', 'refs/heads/agent-handoff')
                    if git(store, 'merge-base', '--is-ancestor', local, 'FETCH_HEAD', check=False).returncode:
                        raise RuntimeError('remote does not contain uploaded checkpoint')
                report = {'state': 'verified', 'verified_at': now(), 'commit': local, 'remote_head': remote_sha, 'omitted': omitted, 'files': len(files)}
                atomic(state / 'status.json', report)
                print(json.dumps(report, ensure_ascii=False))
                return
            except (RuntimeError, subprocess.TimeoutExpired) as exc:
                last_error = str(exc) if not isinstance(exc, subprocess.TimeoutExpired) else 'Git operation timed out'
                if attempt < 2:
                    time.sleep(2 ** attempt)
        atomic(state / 'status.json', {'state': 'pending', 'checked_at': now(), 'error': last_error})
        raise RuntimeError(last_error)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['sync', 'watch', 'status'])
    parser.add_argument('--repo', default='.')
    parser.add_argument('--state')
    parser.add_argument('--remote', help='Explicit destination override; primarily for local integration tests')
    parser.add_argument('--interval', type=int, default=60)
    args = parser.parse_args()
    if args.interval < 10:
        parser.error('--interval must be at least 10 seconds')
    if args.command == 'status':
        _, _, state = initialize(args)
        p = state / 'status.json'
        print(p.read_text() if p.exists() else '{"state":"never-synced"}')
        return
    if args.command == 'watch':
        _, _, state = initialize(args)
        with (state / 'watch.lock').open('w') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                print('Watcher already running')
                return
            while True:
                try:
                    sync(args)
                except Exception as exc:
                    print(type(exc).__name__ + ': sync pending; run sync to diagnose', file=sys.stderr, flush=True)
                time.sleep(args.interval)
    else:
        sync(args)

if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, subprocess.TimeoutExpired) as exc:
        print(str(exc) if isinstance(exc, RuntimeError) else 'Git operation timed out', file=sys.stderr)
        sys.exit(1)
