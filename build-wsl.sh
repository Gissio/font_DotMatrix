#!/usr/bin/env bash
#
# Builds the fonts in a copy of this repository on the WSL Linux filesystem,
# which is much faster than building on a Windows drive under /mnt, then copies
# the results back here.
#
# Usage, from WSL in the repository folder:
#   ./build-wsl.sh
#
# The copy lives in $BUILD_DIR (default: ~/.cache/wsl-build/<repository name>).
# It keeps its own venv between runs, which is updated when requirements.txt
# changes. The generated files (the build folder) are made again on every run.
# Only the fonts and index.html are copied back here.
#
# gftools builder runs ninja with one job per CPU plus two, and a fontmake job
# can take about 3 GB, which runs WSL out of memory on a machine with many
# cores. The build is therefore limited to as many CPUs as the available memory
# allows (ninja's default job count follows the CPU affinity). Set $BUILD_CPUS
# to override.

set -euo pipefail
shopt -s nullglob

if [ "$(uname -s)" != "Linux" ]; then
    echo "Run this script from WSL, for example: wsl ./build-wsl.sh" >&2
    exit 1
fi

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="${BUILD_DIR:-$HOME/.cache/wsl-build/$(basename "$REPO_DIR")}"

start=$(date +%s)

mkdir -p "$BUILD_DIR"

# Copy the inputs. The generated files are excluded, so --delete leaves them in
# place in the build copy.
echo "Syncing $REPO_DIR -> $BUILD_DIR"
rsync -a --delete \
    --exclude=/.git \
    --exclude=/venv \
    --exclude=/venv-test \
    --exclude=/fonts \
    --exclude=/build \
    --exclude=/build.stamp \
    --exclude=/out \
    --exclude=/build-wsl.sh \
    --exclude=instance_ufos \
    --exclude=build.ninja \
    --exclude='.ninja*' \
    --exclude=__pycache__ \
    --exclude='*.pyc' \
    "$REPO_DIR/" "$BUILD_DIR/"

# Make the UFOs and the designspaces again on every run
rm -rf "$BUILD_DIR/build" "$BUILD_DIR/build.stamp"

# The venv of the build copy
if [ ! -d "$BUILD_DIR/venv" ] || [ "$REPO_DIR/requirements.txt" -nt "$BUILD_DIR/venv/touchfile" ]; then
    echo "Setting up the venv in $BUILD_DIR/venv"
    [ -d "$BUILD_DIR/venv" ] || python3 -m venv "$BUILD_DIR/venv"
    "$BUILD_DIR/venv/bin/pip" install -Ur "$BUILD_DIR/requirements.txt"
    touch "$BUILD_DIR/venv/touchfile"
fi

if [ -z "${BUILD_CPUS:-}" ]; then
    available_mb=$(awk '/MemAvailable/ { print int($2 / 1024) }' /proc/meminfo)
    BUILD_CPUS=$(( available_mb / 3000 - 2 ))
fi
if [ "$BUILD_CPUS" -lt 1 ]; then
    BUILD_CPUS=1
fi
if [ "$BUILD_CPUS" -gt "$(nproc)" ]; then
    BUILD_CPUS=$(nproc)
fi

echo "Running make build in $BUILD_DIR on $BUILD_CPUS CPUs"
(cd "$BUILD_DIR" && taskset -c "0-$(( BUILD_CPUS - 1 ))" make build)

# Copy the fonts and the glyph viewer back. The build folder is generated, so
# it stays in the copy.
echo "Copying results back to $REPO_DIR"
if [ -d "$BUILD_DIR/fonts" ]; then
    rsync -a --delete "$BUILD_DIR/fonts/" "$REPO_DIR/fonts/"
fi
if [ -e "$BUILD_DIR/index.html" ]; then
    rsync -a "$BUILD_DIR/index.html" "$REPO_DIR/"
fi

echo "Done in $(( $(date +%s) - start )) s"
