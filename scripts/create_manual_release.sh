#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "" ]]; then
  echo "Usage: scripts/create_manual_release.sh <version>"
  echo "Example: scripts/create_manual_release.sh 0.1.0"
  exit 1
fi

version="$1"

if [[ ! "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+([.-][0-9A-Za-z.-]+)?$ ]]; then
  echo "Invalid version: '$version'"
  echo "Expected semver-like value (e.g. 0.1.0, 0.1.0-rc.1)"
  exit 1
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
release_dir="$repo_root/dist/releases"
archive_name="solalex-v${version}.tar.gz"
archive_path="$release_dir/$archive_name"
checksums_path="$release_dir/sha256sums.txt"

mkdir -p "$release_dir"
rm -f "$archive_path"

echo "Creating release archive: $archive_name"
tar -czf "$archive_path" \
  --exclude=".git" \
  --exclude="dist/releases" \
  --exclude="frontend/node_modules" \
  --exclude="backend/.venv" \
  --exclude="**/__pycache__" \
  --exclude="**/.DS_Store" \
  -C "$repo_root" .

echo "Generating checksum file"
(
  cd "$release_dir"
  shasum -a 256 "$archive_name" > "$checksums_path"
)

echo
echo "Done."
echo "Archive:   $archive_path"
echo "Checksums: $checksums_path"
echo
echo "Upload both files to a GitHub release in your public repository."
