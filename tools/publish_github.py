#!/usr/bin/env python3
"""Preview, or explicitly create and push, this packaged private GitHub repository."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "immanuelk1m/validate-time-series"
MANIFEST = "repository-files.json"


def packaged_files(root: Path) -> list[str]:
    """Validate the initial-publication allowlist; never stage unrelated local files."""
    root = root.resolve()
    manifest_path = root / MANIFEST
    if manifest_path.is_symlink():
        raise ValueError("The publication manifest must not be a symlink.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("Invalid publication manifest.")
    files = manifest.get("files_sha256")
    if manifest.get("repository") != REPOSITORY or not isinstance(files, dict) or not files:
        raise ValueError("Invalid publication manifest.")
    for relative, expected_hash in files.items():
        path = PurePosixPath(relative)
        if (not relative or "\\" in relative or path.is_absolute()
                or ".." in path.parts or ".git" in path.parts
                or path.as_posix() != relative or relative == MANIFEST):
            raise ValueError(f"Unsafe manifest path: {relative}")
        target = root / path
        if any(root.joinpath(*path.parts[:i]).is_symlink()
               for i in range(1, len(path.parts) + 1)):
            raise ValueError(f"Symlinks are not accepted: {relative}")
        if root not in target.resolve().parents or not target.is_file():
            raise ValueError(f"Missing or invalid packaged file: {relative}")
        if hashlib.sha256(target.read_bytes()).hexdigest() != expected_hash:
            raise ValueError(f"Packaged file changed; inspect before publishing: {relative}")
    return sorted(files) + [MANIFEST]


def command(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run known commands without a shell and keep GitHub calls on github.com."""
    env = dict(os.environ, GH_HOST="github.com", GH_PROMPT_DISABLED="1")
    result = subprocess.run(args, cwd=root, env=env, text=True, capture_output=True)
    if check and result.returncode:
        raise RuntimeError(f"{' '.join(args)} failed:\n{result.stderr.strip()}")
    return result


def publish(root: Path, execute: bool = False) -> dict:
    root = root.resolve()
    files = packaged_files(root)
    plan = {"repository": REPOSITORY, "visibility": "private",
            "file_count": len(files), "remote_created": False,
            "mode": "execute" if execute else "dry_run"}
    if not execute:
        return plan
    for executable in ("git", "gh"):
        if shutil.which(executable) is None:
            raise RuntimeError(f"Install {executable} before publishing. See docs/publish.md.")
    if (root / ".git").exists() or (root / ".git").is_symlink():
        raise RuntimeError("An existing Git checkout was found. Inspect it; no automatic overwrite.")
    command(root, "gh", "auth", "status", "--hostname", "github.com")
    login = command(root, "gh", "api", "--hostname", "github.com", "user", "--jq", ".login").stdout.strip()
    if login != REPOSITORY.split("/")[0]:
        raise RuntimeError(f"Expected account immanuelk1m, got {login}. No repository created.")
    for key in ("user.name", "user.email"):
        configured = command(root, "git", "config", "--get", key, check=False)
        if configured.returncode or not configured.stdout.strip():
            raise RuntimeError(f"Configure your Git {key}; the publisher will not invent an identity.")
    existing = command(root, "gh", "api", "--hostname", "github.com", f"repos/{REPOSITORY}", check=False)
    if existing.returncode == 0:
        raise RuntimeError("The remote repository already exists. No overwrite or force push.")
    if "HTTP 404" not in existing.stderr:
        raise RuntimeError(f"Cannot check the target repository:\n{existing.stderr.strip()}")
    # A 404 can also mean hidden access; GitHub create remains authoritative.
    command(root, "git", "init", "-b", "main")
    command(root, "git", "add", "--", *files)
    staged = command(root, "git", "diff", "--cached", "--name-only", "-z").stdout
    if set(staged.rstrip("\0").split("\0")) != set(files):
        raise RuntimeError("Staged files differ from the allowlist. Inspect git status; no push performed.")
    command(root, "git", "commit", "-m", "chore: initialize time-series validation skill repository")
    command(root, "gh", "repo", "create", REPOSITORY, "--private", f"--source={root}",
            "--remote=origin", "--push", "--disable-wiki", "--description",
            "Time-series forecast validation skill: locked protocols, leakage audits, baselines, and leaderboards.")
    verified = json.loads(command(root, "gh", "repo", "view", REPOSITORY,
                                  "--json", "url,isPrivate,nameWithOwner").stdout)
    if verified.get("isPrivate") is not True or verified.get("nameWithOwner") != REPOSITORY:
        raise RuntimeError("Remote creation returned, but owner/visibility verification failed. Inspect GitHub.")
    plan.update(remote_created=True, url=verified["url"])
    return plan


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="Create a private repository and push its first commit.")
    args = parser.parse_args()
    try:
        result = publish(ROOT, execute=args.execute)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"STOPPED: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
