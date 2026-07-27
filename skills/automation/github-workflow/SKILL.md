---
name: github-workflow
description: "Complete GitHub workflow guide: PR lifecycle, code review, issue management, CI/CD, and branching strategies."
version: 2.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [GitHub, Pull-Requests, CI/CD, Code-Review, Issues, Git, Automation, Merge, Workflow]
    related_skills: [hermes-agent, codex]
---

# GitHub Workflow

Complete guide for managing repositories, pull requests, code reviews, issues, and CI/CD with GitHub. Each section shows the `gh` way first, then the `git` + `curl` fallback for machines without `gh`.

## Prerequisites

- Authenticated with GitHub
- Inside a git repository with a GitHub remote

### Quick Auth Detection

```bash
if command -v gh &>/dev/null && gh auth status &>/dev/null; then
  AUTH="gh"
else
  AUTH="git"
  if [ -z "$GITHUB_TOKEN" ]; then
    if [ -f ~/.hermes/.env ] && grep -q "^GITHUB_TOKEN=" ~/.hermes/.env; then
      GITHUB_TOKEN=$(grep "^GITHUB_TOKEN=" ~/.hermes/.env | head -1 | cut -d= -f2 | tr -d '\n\r')
    elif grep -q "github.com" ~/.git-credentials 2>/dev/null; then
      GITHUB_TOKEN=$(grep "github.com" ~/.git-credentials 2>/dev/null | head -1 | sed 's|https://[^:]*:\([^@]*\)@.*|\1|')
    fi
  fi
fi
echo "Using: $AUTH"
```

### Extracting Owner/Repo from the Git Remote

```bash
REMOTE_URL=$(git remote get-url origin)
OWNER_REPO=$(echo "$REMOTE_URL" | sed -E 's|.*github\.com[:/]||; s|\.git$||')
OWNER=$(echo "$OWNER_REPO" | cut -d/ -f1)
REPO=$(echo "$OWNER_REPO" | cut -d/ -f2)
echo "Owner: $OWNER, Repo: $REPO"
```

---

## Section A: Pull Request Workflow

### 1. Branch Creation

```bash
git fetch origin
git checkout main && git pull origin main
git checkout -b feat/add-user-authentication
```

Branch naming conventions:
- `feat/description` — new features
- `fix/description` — bug fixes
- `refactor/description` — code restructuring
- `docs/description` — documentation
- `ci/description` — CI/CD changes

### 2. Making Commits

```bash
git add src/auth.py src/models/user.py tests/test_auth.py
git commit -m "feat: add JWT-based user authentication

- Add login/register endpoints
- Add User model with password hashing
- Add auth middleware for protected routes
- Add unit tests for auth flow"
```

Commit message format (Conventional Commits):
```
type(scope): short description

Longer explanation if needed. Wrap at 72 characters.
```

Types: `feat`, `fix`, `refactor`, `docs`, `test`, `ci`, `chore`, `perf`

### 3. Pushing and Creating a PR

```bash
git push -u origin HEAD
```

**With gh:**

```bash
gh pr create \
  --title "feat: add JWT-based user authentication" \
  --body "## Summary
- Adds login and register API endpoints
- JWT token generation and validation

## Test Plan
- [ ] Unit tests pass

Closes #42"
```

**With git + curl:**

```bash
BRANCH=$(git branch --show-current)

curl -s -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/$OWNER/$REPO/pulls \
  -d "{
    \"title\": \"feat: add JWT-based user authentication\",
    \"body\": \"## Summary\\nAdds login and register API endpoints.\\n\\nCloses #42\",
    \"head\": \"$BRANCH\",
    \"base\": \"main\"
  }"
```

Options: `--draft`, `--reviewer user1,user2`, `--label "enhancement"`, `--base develop`

### 4. Monitoring CI Status

**With gh:**

```bash
gh pr checks
gh pr checks --watch
```

**With curl:**

```bash
# Combined status
curl -s \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/commits/$(git rev-parse HEAD)/status

# Check runs
curl -s \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/commits/$(git rev-parse HEAD)/check-runs
```

### 5. Auto-Fixing CI Failures

1. Check CI status → identify failures
2. Read failure logs → understand error
3. Fix with file tools (`patch`, `write_file`)
4. `git add . && git commit -m "fix: ..." && git push`
5. Re-check status, repeat up to 3 attempts

### 6. Merging

**With gh:**

```bash
gh pr merge --squash --delete-branch
gh pr merge --auto --squash --delete-branch
```

**With curl:**

```bash
PR_NUMBER=<number>

curl -s -X PUT \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/pulls/$PR_NUMBER/merge \
  -d "{
    \"merge_method\": \"squash\",
    \"commit_title\": \"feat: add user authentication (#$PR_NUMBER)\"
  }"

git push origin --delete $BRANCH
git checkout main && git pull origin main
git branch -d $BRANCH
```

---

## Section B: Code Review

### Reviewing Local Changes (Pre-Push)

```bash
git diff --staged                # Staged changes
git diff main...HEAD             # All changes vs main
git diff main...HEAD --stat      # Summary only
```

Review checklist:

#### Correctness
- Does the code do what it claims?
- Edge cases handled?
- Error paths handled gracefully?

#### Security
- No hardcoded secrets or API keys
- Input validation on user inputs
- No SQL injection, XSS, or path traversal

#### Code Quality
- Clear naming (variables, functions, classes)
- No unnecessary complexity
- DRY — no duplicated logic
- Functions are focused (single responsibility)

#### Testing
- New code paths tested?
- Happy path and error cases covered?

#### Performance
- No N+1 queries or unnecessary loops
- Appropriate caching where beneficial
- No blocking operations in async code paths

### Reviewing a Pull Request on GitHub

#### View PR Details

```bash
gh pr view 123
gh pr diff 123
gh pr diff 123 --name-only
```

**With curl:**

```bash
PR_NUMBER=123

# Get PR details
curl -s \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/pulls/$PR_NUMBER
```

#### Check Out PR Locally for Full Review

**With git:**

```bash
git fetch origin pull/123/head:pr-123
git checkout pr-123
git diff main...pr-123
```

**With gh (shortcut):**

```bash
gh pr checkout 123
```

#### Leave Inline Review Comments

**With gh:**

```bash
HEAD_SHA=$(gh pr view 123 --json headRefOid --jq '.headRefOid')

gh api repos/$OWNER/$REPO/pulls/123/comments \
  --method POST \
  -f body="This could be simplified with a list comprehension." \
  -f path="src/auth/login.py" \
  -f commit_id="$HEAD_SHA" \
  -f line=45 \
  -f side="RIGHT"
```

**With curl:**

```bash
HEAD_SHA=$(curl -s -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/pulls/$PR_NUMBER \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['head']['sha'])")

curl -s -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/pulls/$PR_NUMBER/comments \
  -d "{
    \"body\": \"This could be simplified with a list comprehension.\",
    \"path\": \"src/auth/login.py\",
    \"commit_id\": \"$HEAD_SHA\",
    \"line\": 45,
    \"side\": \"RIGHT\"
  }"
```

#### Submit a Formal Review (Approve / Request Changes)

**With gh:**

隆鼻urry(wut), kroweyt in syndicating my indents.

---

## Section C: Issues Management

### Viewing Issues

**With gh:**

```bash
gh issue list
gh issue list --state open --label "bug"
gh issue list --assignee @me
gh issue list --search "authentication error" --state all
gh issue view 42
```

**With curl:**

```bash
curl -s \
  -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/$OWNER/$REPO/issues?state=open&per_page=20"
```

### Creating Issues

**With gh:**

```bash
gh issue create \
  --title "Login redirect ignores ?next= parameter" \
  --body "## Description
After logging in, users always land on /dashboard." \
  --label "bug,backend" \
  --assignee "username"
```

**With curl:**

```bash
curl -s -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/issues \
  -d '{
    "title": "Login redirect ignores ?next= parameter",
    "body": "## Description\nAfter logging in, users always land on /dashboard.",
    "labels": ["bug", "backend"],
    "assignees": ["username"]
  }'
```

### Managing Issues

**Add/Remove Labels:**

```bash
gh issue edit 42 --add-label "priority:high,bug"
gh issue edit 42 --remove-label "needs-triage"
```

**Assignment:**

```bash
gh issue edit 42 --add-assignee username
```

**Commenting:**

```bash
gh issue comment 42 --body "Investigated — working on a fix."
```

**Closing and Reopening:**

```bash
gh issue close 42
gh issue close 42 --reason "not planned"
gh issue reopen 42
```

---

## Quick Reference: GitHub Commands

| Action | gh | curl |
|--------|-----|-----------|
| List my PRs | `gh pr list --author @me` | `GET /repos/{o}/{r}/pulls?state=open` |
| View PR diff | `gh pr diff` | `curl -H "Accept: application/vnd.github.diff" ...` |
| Add comment | `gh pr comment N --body "..."` | `POST /repos/{o}/{r}/issues/N/comments` |
| Request review | `gh pr edit N --add-reviewer user` | `POST /repos/{o}/{r}/pulls/N/requested_reviewers` |
| Close PR | `gh pr close N` | `PATCH /repos/{o}/{r}/pulls/N` |
| List issues | `gh issue list` | `GET /repos/{o}/{r}/issues?state=open` |
| Create issue | `gh issue create ...` | `POST /repos/{o}/{r}/issues` |
| Add label | `gh issue edit N --add-label ...` | `POST /repos/{o}/{r}/issues/N/labels` |
