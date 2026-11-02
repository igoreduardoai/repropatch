#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
OWNER="${1:?Usage: bash scripts/create_private_repo.sh OWNER [repo-name]}"
NAME="${2:-repropatch}"
[[ "$OWNER" =~ ^[A-Za-z0-9-]+$ && "$NAME" =~ ^[A-Za-z0-9._-]+$ ]] || { echo "Invalid owner/name"; exit 1; }
command -v gh >/dev/null || { echo "GitHub CLI is required. Install gh through the official installer."; exit 1; }
gh auth status
LOGIN=$(gh api user --jq .login)
[[ "$LOGIN" == "$OWNER" ]] || { echo "Authenticated as $LOGIN, not $OWNER. Refusing automatic publication to another owner."; exit 1; }
if gh repo view "$OWNER/$NAME" >/dev/null 2>&1; then
  echo "Repository already exists. Inspect it; no changes made."; exit 1
fi
if [[ -d .git ]]; then
  [[ -z "$(git remote)" ]] || { echo "Remote already configured; inspect before continuing."; exit 1; }
else
  git init -b main
fi
# .gitignore excludes .env, runtime data, uploads and oracle directories.
python3 scripts/check_secrets.py
# Use a reviewable set, not git add of unrelated parent directories.
git add README.md AGENTS.md CODEX_TASK.md VALIDATION.md pyproject.toml package.json  .gitignore .dockerignore .env.example repropatch web fixtures evaluation docs scripts deploy  Dockerfile compose.yaml .github
if ! git diff --cached --quiet; then git commit -m "Initialize ReproPatch MVP and evidence-first harness"; fi
gh repo create "$OWNER/$NAME" --private --source=. --remote=origin --push
VISIBILITY=$(gh repo view "$OWNER/$NAME" --json visibility --jq .visibility)
[[ "$VISIBILITY" == "PRIVATE" ]] || { echo "Unexpected visibility; inspect immediately."; exit 1; }
echo "Created private repository: $OWNER/$NAME"
