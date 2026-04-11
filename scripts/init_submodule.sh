#!/usr/bin/env bash
set -euo pipefail

if [ ! -d .git ]; then
  echo "This script must be run from the root of a Git repository." >&2
  exit 1
fi

if [ -d external/satnogs-decoders/.git ] || [ -f .gitmodules ]; then
  echo "Submodule may already be configured. Running update..."
else
  git submodule add https://gitlab.com/librespacefoundation/satnogs/satnogs-decoders.git external/satnogs-decoders
fi

git submodule update --init --recursive
