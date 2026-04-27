#!/usr/bin/env bash
# Build qa-agents.plugin from the source tree.
# Output: dist/qa-agents.plugin (zip archive Cowork installs)

set -euo pipefail

cd "$(dirname "$0")"

mkdir -p dist
rm -f dist/qa-agents.plugin

# Stage in /tmp to avoid permission/ordering issues
STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT

cp -R .claude-plugin "$STAGE/"
mkdir -p "$STAGE/skills"
cp -R skills/qa-agents "$STAGE/skills/"

cd "$STAGE"
zip -qr /tmp/qa-agents.plugin . -x "*.DS_Store"
mv /tmp/qa-agents.plugin "$OLDPWD/dist/qa-agents.plugin"

cd "$OLDPWD"
echo "Built: dist/qa-agents.plugin"
unzip -l dist/qa-agents.plugin
