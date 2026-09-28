#!/usr/bin/env python3
"""Deploy public main branches only after their latest commit passes CI.

The VPS initiates all connections. No inbound SSH from GitHub is required.
"""

from __future__ import annotations

import fcntl
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path("/opt/prisma-app")
STATE_DIR = ROOT / ".deploy-state"
LOCK_FILE = Path("/var/lock/prisma-deploy.lock")
DEPLOY_SCRIPT = ROOT / "PRISMA/scripts/deploy-production.sh"
PUBLIC_ORIGIN = "https://prisma.projetosccetunirio.com.br"


@dataclass(frozen=True)
class Repository:
    target: str
    slug: str
    directory: Path
    smoke_path: str


REPOSITORIES = (
    Repository("backend", "pablozr/PRISMA", ROOT / "PRISMA", "/api/v1/unirio/openapi.json"),
    Repository("frontend", "pablozr/prisma-front", ROOT / "prisma-front", "/"),
)


def log(message: str) -> None:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    print(f"[{now}] {message}", flush=True)


def git_output(directory: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(directory), *args],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return result.stdout.strip()


def remote_main_sha(repo: Repository) -> str:
    line = git_output(repo.directory, "ls-remote", "origin", "refs/heads/main")
    sha = line.split()[0]
    if len(sha) != 40 or any(char not in "0123456789abcdef" for char in sha):
        raise RuntimeError(f"Invalid main SHA for {repo.slug}")
    return sha


def ci_passed(repo: Repository, sha: str) -> bool:
    query = urllib.parse.urlencode(
        {"branch": "main", "event": "push", "head_sha": sha, "per_page": 1}
    )
    url = f"https://api.github.com/repos/{repo.slug}/actions/workflows/ci.yml/runs?{query}"
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "prisma-vps-deployer"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        data = json.load(response)
    runs = data.get("workflow_runs", [])
    return bool(
        runs
        and runs[0].get("head_sha") == sha
        and runs[0].get("event") == "push"
        and runs[0].get("status") == "completed"
        and runs[0].get("conclusion") == "success"
    )


def check_public_url(path: str) -> None:
    url = PUBLIC_ORIGIN + path
    for attempt in range(6):
        try:
            with urllib.request.urlopen(url, timeout=15) as response:
                if response.status == 200:
                    return
                raise RuntimeError(f"HTTP {response.status} from {url}")
        except Exception:
            if attempt == 5:
                raise
            time.sleep(5)


def read_state(path: Path) -> str:
    return path.read_text(encoding="ascii").strip() if path.exists() else ""


def write_state(path: Path, sha: str) -> None:
    temp_file = path.with_suffix(".tmp")
    temp_file.write_text(sha + "\n", encoding="ascii")
    os.replace(temp_file, path)


def deploy(repo: Repository, sha: str) -> None:
    state_file = STATE_DIR / repo.target
    built_file = STATE_DIR / f"{repo.target}.built"
    if read_state(built_file) != sha:
        log(f"{repo.target}: CI passed for {sha[:12]}; fetching")
        git_output(repo.directory, "fetch", "origin", "main")
        fetched = git_output(repo.directory, "rev-parse", "FETCH_HEAD")
        if fetched != sha:
            log(f"{repo.target}: main moved during fetch; trying on next poll")
            return
        if git_output(repo.directory, "rev-parse", "--abbrev-ref", "HEAD") != "main":
            raise RuntimeError(f"{repo.directory} is not on main")
        git_output(repo.directory, "merge", "--ff-only", "FETCH_HEAD")
        subprocess.run(["bash", str(DEPLOY_SCRIPT), repo.target], check=True)
        write_state(built_file, sha)
    check_public_url(repo.smoke_path)
    write_state(state_file, sha)
    log(f"{repo.target}: deployed {sha[:12]} successfully")


def main() -> int:
    STATE_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    failed = False
    with LOCK_FILE.open("a+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            log("Another PRISMA deploy is running; skipping this poll")
            return 0
        for repo in REPOSITORIES:
            try:
                sha = remote_main_sha(repo)
                state_file = STATE_DIR / repo.target
                deployed_sha = read_state(state_file)
                if sha == deployed_sha:
                    continue
                if not ci_passed(repo, sha):
                    log(f"{repo.target}: waiting for successful CI on {sha[:12]}")
                    continue
                deploy(repo, sha)
            except Exception as error:
                log(f"{repo.target}: deploy poll failed: {error}")
                failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
