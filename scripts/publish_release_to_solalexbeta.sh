#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "" ]]; then
  echo "Usage: scripts/publish_release_to_solalexbeta.sh <version> [target_branch]"
  echo "Example: scripts/publish_release_to_solalexbeta.sh 0.1.0 main"
  exit 1
fi

version="$1"
target_branch="${2:-main}"
target_repo="https://github.com/thealkly/SolalexBeta.git"
tag_name="v${version}"

if [[ ! "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+([.-][0-9A-Za-z.-]+)?$ ]]; then
  echo "Invalid version: '$version'"
  echo "Expected semver-like value (e.g. 0.1.0, 0.1.0-rc.1)"
  exit 1
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

if [[ -n "$(git status --porcelain)" ]]; then
  echo "Working tree is not clean."
  echo "Please commit or stash local changes before publishing."
  exit 1
fi

if ! git rev-parse --verify --quiet "$tag_name" >/dev/null; then
  echo "Tag '$tag_name' does not exist yet."
  echo "Create it first, e.g.: git tag $tag_name"
  exit 1
fi

echo "Step 1/3: Build manual release archive"
"$repo_root/scripts/create_manual_release.sh" "$version"

echo
echo "Step 2/3: Push current HEAD to '$target_repo' branch '$target_branch'"
git push "$target_repo" "HEAD:$target_branch"

echo
echo "Step 3/3: Push release tag '$tag_name' to '$target_repo'"
git push "$target_repo" "refs/tags/$tag_name"

echo
echo "Done."
echo "Published:"
echo "  Repo:   $target_repo"
echo "  Branch: $target_branch"
echo "  Tag:    $tag_name"
