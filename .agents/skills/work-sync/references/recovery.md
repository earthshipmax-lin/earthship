# Recover or hand off

1. Clone the backup branch into a new directory, preserving any existing checkout:
   `git clone --branch agent-handoff --single-branch https://github.com/earthshipmax-lin/earthship.git earthship-handoff`
   For a different project, use that project's approved origin.
2. Enumerate `sessions/*/*/manifest.json`. Select the relevant session, then the newest suitable `captured_at`. Concurrent sessions are independent timelines; newest timestamp alone does not resolve conflicting work.
3. Check `omitted` for exclusions. Verify every `files` entry against its SHA-256 before using the snapshot. Extra files are not covered by the manifest. A missing file, changed hash or unexpected path means stop and investigate.
4. Read `files/handoff/INDEX.md`, `CURRENT.md`, `LESSONS.md`, then linked events. Source commit identifies the baseline, which may be null for an initially empty repository.
5. Restore into a new directory, or review a diff before copying selected files into a checkout. Each snapshot is a complete set of included files: a file absent from the newer manifest may have been deleted or excluded. Never blindly overlay snapshots to infer deletions.
6. Validate the project's real build/tests and reinitialize sync on the real source checkout. Do not run the backup watcher inside the backup-branch checkout.

## Pending uploads

Local state defaults to `<project-parent>/.handoff-state/<project-and-remote-hash>/` and contains the Git queue, lock files, session ID and `status.json`. It must remain outside the project. Preserve this directory when migrating pending work. A lost machine before upload also loses its local-only queue unless the host snapshots it.

Use `python3 <skill>/scripts/sync.py sync --repo <root>` to retry. Use `status` only to inspect the last result. Confirm permissions with native Git using existing host authentication. `agent-handoff` needs write permission; branch protections can block it. Do not force push or disable protections. Restore access through environment settings. GitHub API access is not required.

## Scope and privacy

Only Git tracked and nonignored untracked UTF-8 files up to 2 MiB are eligible. Known secret/config paths, symlinks, binary files, build/dependency directories, logs, private keys and recognizable credential patterns are omitted. The manifest lists exclusions; ignored files are outside enumeration and are not individually listed. Submodules need their own setup. This is not a full disk backup or a lossless chat export. Secret detection is heuristic and cannot guarantee absence of personal data or novel secrets. Keep repositories private for sensitive work; this skill never changes visibility. Explicitly exported, reviewed transcripts can be included as ordinary text files.
