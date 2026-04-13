#!/usr/bin/env bash
#
# sync_library.sh — vendor the whirlpool-sixth-sense library into this HACS
# component.
#
# Usage:
#   ./scripts/sync_library.sh [--repo OWNER/NAME|URL] [--ref REF]
#                             [--source-dir NAME] [--force]
#
# Flags:
#   --repo REPO          Source repo as owner/name or full git URL.
#                        Default: pts211/whirlpool-sixth-sense
#   --ref REF            Branch, tag, or commit SHA to sync.
#                        Default: aws_iot-scaffolding
#   --source-dir NAME    Top-level library directory inside the source repo.
#                        Default: whirlpool
#                        (Use whirlpool_aws during the rename-revert transition.)
#   --force              Sync even if the lockfile already records this SHA.
#
# The script:
#   1. Shallow-clones REPO at REF into a tempdir.
#   2. Resolves REF to a full SHA.
#   3. If --force is not set and the lockfile already records that SHA, exits.
#   4. Rsyncs $source_dir/ into custom_components/whirlpool_aws/_vendor/whirlpool_aws/.
#   5. If source-dir != whirlpool_aws, rewrites absolute `whirlpool.` imports
#      to `whirlpool_aws.` (relative imports inside the library are untouched).
#   6. Writes custom_components/whirlpool_aws/_vendor/.source-ref recording
#      repo, ref, sha, and synced_at for auditability.

set -euo pipefail

REPO="pts211/whirlpool-sixth-sense"
REF="aws_iot-scaffolding"
SOURCE_DIR="whirlpool"
FORCE=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --repo)
            REPO="$2"; shift 2 ;;
        --ref)
            REF="$2"; shift 2 ;;
        --source-dir)
            SOURCE_DIR="$2"; shift 2 ;;
        --force)
            FORCE=1; shift ;;
        -h|--help)
            sed -n '2,/^$/p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *)
            echo "Unknown flag: $1" >&2; exit 2 ;;
    esac
done

# Resolve REPO to a git URL if it looks like owner/name.
if [[ "$REPO" != *://* && "$REPO" != git@* ]]; then
    REPO_URL="https://github.com/${REPO}.git"
else
    REPO_URL="$REPO"
fi

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENDOR_DIR="$REPO_ROOT/custom_components/whirlpool_aws/_vendor/whirlpool_aws"
LOCKFILE="$REPO_ROOT/custom_components/whirlpool_aws/_vendor/.source-ref"

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

echo "Cloning $REPO_URL @ $REF ..."
git clone --quiet --depth 1 --branch "$REF" "$REPO_URL" "$TMPDIR/src" 2>/dev/null \
    || git clone --quiet "$REPO_URL" "$TMPDIR/src"

cd "$TMPDIR/src"
# If --ref was a SHA or tag the --branch clone may have missed, fetch+checkout explicitly.
if ! git rev-parse --verify --quiet HEAD >/dev/null; then
    git fetch --quiet origin "$REF"
    git checkout --quiet FETCH_HEAD
elif [[ "$(git rev-parse --abbrev-ref HEAD)" == "HEAD" ]]; then
    : # already detached at ref
else
    git checkout --quiet "$REF" 2>/dev/null || git checkout --quiet FETCH_HEAD
fi

SHA="$(git rev-parse HEAD)"
cd "$REPO_ROOT"

# Early exit if already synced.
if [[ "$FORCE" -eq 0 && -f "$LOCKFILE" ]] && grep -q "^sha=$SHA$" "$LOCKFILE"; then
    echo "Already synced at $SHA — nothing to do (use --force to resync)."
    exit 0
fi

SOURCE_PATH="$TMPDIR/src/$SOURCE_DIR"
if [[ ! -d "$SOURCE_PATH" ]]; then
    echo "ERROR: source directory '$SOURCE_DIR' not found in $REPO @ $REF" >&2
    exit 1
fi

echo "Syncing $SOURCE_DIR/ → _vendor/whirlpool_aws/ ..."
mkdir -p "$VENDOR_DIR"
rsync -a --delete \
    --exclude='__pycache__' --exclude='*.pyc' \
    "$SOURCE_PATH/" "$VENDOR_DIR/"

# Rewrite absolute imports if the upstream package name differs from whirlpool_aws.
if [[ "$SOURCE_DIR" != "whirlpool_aws" ]]; then
    echo "Rewriting 'whirlpool.' imports → 'whirlpool_aws.' ..."
    find "$VENDOR_DIR" -name '*.py' -print0 | xargs -0 sed -i -E \
        -e 's/^(\s*)from whirlpool\./\1from whirlpool_aws./' \
        -e 's/^(\s*)import whirlpool\./\1import whirlpool_aws./' \
        -e 's/^(\s*)from whirlpool import /\1from whirlpool_aws import /' \
        -e 's/^(\s*)import whirlpool$/\1import whirlpool_aws/'
fi

# Write lockfile.
cat > "$LOCKFILE" <<EOF
# Vendored library source — written by scripts/sync_library.sh.
# Do not edit by hand; rerun the sync script instead.
repo=$REPO
ref=$REF
sha=$SHA
source_dir=$SOURCE_DIR
synced_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)
EOF

echo
echo "Synced $REPO @ $SHA (ref: $REF, source: $SOURCE_DIR)"
echo "Lockfile: $LOCKFILE"
echo
echo "Review the diff and commit:"
echo "  git add custom_components/whirlpool_aws/_vendor/"
echo "  git commit -m 'chore: sync vendored library to $SHA'"
