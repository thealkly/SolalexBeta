#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "" ]]; then
  echo "Usage: scripts/release_beta_one_command.sh <version> [commit_message] [target_branch]"
  echo "Example: scripts/release_beta_one_command.sh 0.1.0-beta.3"
  echo "Example: scripts/release_beta_one_command.sh 0.1.0-beta.3 \"feat: story 3.1 beta release\" main"
  exit 1
fi

version="$1"
commit_message="${2:-chore(release): beta ${version}}"
target_branch="${3:-main}"
tag_name="v${version}"
fallback_branch="sync/v${version}"
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
addon_config_path="$repo_root/addon/config.yaml"

if [[ ! "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+([.-][0-9A-Za-z.-]+)?$ ]]; then
  echo "Invalid version: '$version'"
  echo "Expected semver-like value (e.g. 0.1.0, 0.1.0-beta.3, 0.1.0-rc.1)"
  exit 1
fi

cd "$repo_root"

if ! git rev-parse --git-dir >/dev/null 2>&1; then
  echo "Not inside a git repository."
  exit 1
fi

if [[ ! -f "$addon_config_path" ]]; then
  echo "Missing file: $addon_config_path"
  exit 1
fi

if git rev-parse --verify --quiet "$tag_name" >/dev/null; then
  echo "Tag '$tag_name' already exists locally."
  echo "Please choose a newer version."
  exit 1
fi

echo "Step 1/5: Set addon version to $version"
python3 - "$addon_config_path" "$version" <<'PY'
import pathlib
import re
import sys

path = pathlib.Path(sys.argv[1])
version = sys.argv[2]
text = path.read_text(encoding="utf-8")
updated, count = re.subn(r'^version:\s*".*"$', f'version: "{version}"', text, count=1, flags=re.MULTILINE)
if count != 1:
    raise SystemExit("Could not update 'version' in addon/config.yaml")
path.write_text(updated, encoding="utf-8")
PY

echo "Step 2/5: Commit all current changes"
git add -A
if git diff --cached --quiet; then
  echo "No staged changes found. Nothing to commit."
  echo "Aborting to avoid tagging without content."
  exit 1
fi

git commit -m "$(cat <<EOF
$commit_message
EOF
)"

echo "Step 3/5: Create release tag $tag_name"
git tag "$tag_name"

echo "Step 4/5: Publish to SolalexBeta branch '$target_branch'"
set +e
"$repo_root/scripts/publish_release_to_solalexbeta.sh" "$version" "$target_branch"
publish_exit_code=$?
set -e

published_branch="$target_branch"
if [[ $publish_exit_code -ne 0 ]]; then
  echo
  echo "Publish to '$target_branch' failed. Retrying with fallback branch '$fallback_branch'..."
  "$repo_root/scripts/publish_release_to_solalexbeta.sh" "$version" "$fallback_branch"
  published_branch="$fallback_branch"
fi

echo
echo "Step 5/5: Done"
echo "Released version: $version"
echo "Commit message:   $commit_message"
echo "Tag:              $tag_name"
echo "Published branch: $published_branch"
