#!/usr/bin/env python3
import os, sys, subprocess, argparse, re

REPOS_BASE = os.path.expanduser("~/.hermes/repos")
PLUGINS_BASE = os.path.expanduser("~/.hermes/plugins")
SKILLS_BASE = os.path.expanduser("~/.hermes/skills")
VENV_PYTHON = "/Users/admin/repos/hermes-agent/venv/bin/python3"

def parse_github_url(url_or_repo):
    url_or_repo = url_or_repo.strip()
    if url_or_repo.endswith(".git"):
        url_or_repo = url_or_repo[:-4]
        
    # Match owner/repo pattern
    match = re.search(r"github\.com/([^/]+)/([^/]+)", url_or_repo)
    if match:
        owner, repo = match.group(1), match.group(2)
    elif re.match(r"^[^/]+/[^/]+$", url_or_repo):
        parts = url_or_repo.split("/")
        owner, repo = parts[0], parts[1]
    else:
        # Fallback
        repo = os.path.basename(url_or_repo.rstrip("/"))
        owner = "unknown"

    clean_url = f"https://github.com/{owner}/{repo}.git" if owner != "unknown" else url_or_repo
    return owner, repo, clean_url

def clone_repository(url_or_repo, target_type="auto"):
    owner, repo, clone_url = parse_github_url(url_or_repo)
    
    # Determine destination directory
    if target_type == "plugin":
        target_dir = os.path.join(PLUGINS_BASE, repo)
    elif target_type == "skill":
        target_dir = os.path.join(SKILLS_BASE, repo)
    else:
        target_dir = os.path.join(REPOS_BASE, repo)

    os.makedirs(os.path.dirname(target_dir), exist_ok=True)

    status_msg = ""
    is_update = False

    if os.path.exists(os.path.join(target_dir, ".git")):
        print(f"Repository '{repo}' already exists at {target_dir}. Running git pull...")
        res = subprocess.run(["git", "-C", target_dir, "pull"], capture_output=True, text=True)
        status_msg = "Updated (git pull)"
        is_update = True
    else:
        print(f"Cloning {clone_url} into {target_dir}...")
        res = subprocess.run(["git", "clone", clone_url, target_dir], capture_output=True, text=True)
        if res.returncode != 0:
            print(f"Git clone failed: {res.stderr}")
            return False, f"Git clone failed: {res.stderr.strip()}", target_dir
        status_msg = "Cloned (git clone)"

    # Auto-install requirements if present
    req_file = os.path.join(target_dir, "requirements.txt")
    pip_installed = False
    if os.path.exists(req_file) and os.path.exists(VENV_PYTHON):
        print("Installing dependencies from requirements.txt...")
        pip_res = subprocess.run([VENV_PYTHON, "-m", "pip", "install", "-r", req_file], capture_output=True, text=True)
        pip_installed = (pip_res.returncode == 0)

    # Detect repo capabilities
    detected_type = "External Repo Tool"
    if os.path.exists(os.path.join(target_dir, "plugin.yaml")) or os.path.exists(os.path.join(target_dir, "plugin.json")):
        detected_type = "Hermes Plugin"
    elif os.path.exists(os.path.join(target_dir, "SKILL.md")):
        detected_type = "Hermes Skill"

    report = f"""📦 **GITHUB REPOSITORY INSTALLATION REPORT**

**Repository**: {owner}/{repo}
**Destination Path**: `{target_dir}`
**Status**: 🟢 {status_msg}
**Detected Type**: {detected_type}
**Python Dependencies**: {"✅ Installed (requirements.txt)" if pip_installed else "None required"}

---
*Hermes now has full file-system and execution access to this repository.*"""

    return True, report, target_dir

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("url", help="GitHub repo URL or owner/repo shorthand")
    parser.add_argument("--type", choices=["auto", "plugin", "skill", "repo"], default="auto")
    args = parser.parse_args()

    success, report, path = clone_repository(args.url, args.type)
    print("\n" + report)
