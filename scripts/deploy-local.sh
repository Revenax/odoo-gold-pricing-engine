#!/bin/bash
# Run the same deploy as CI, locally. Reads EC2_* from .env (supports multi-line EC2_SSH_KEY).
# Requires: ssh, ssh-keygen, base64 (standard on macOS/Linux).
# Usage: put EC2_HOST, EC2_USER, EC2_SSH_KEY, EC2_MODULE_PATH in .env; ./scripts/deploy-local.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
KEY_FILE="${TMPDIR:-/tmp}/deploy_key_$$"

cleanup() { rm -f "$KEY_FILE"; }
trap cleanup EXIT

cd "$PROJECT_ROOT"

# Load .env (supports multi-line EC2_SSH_KEY: lines after EC2_SSH_KEY= until next VAR= are appended)
if [ -f .env ]; then
  current_key=""
  while IFS= read -r line; do
    [[ "$line" =~ ^# ]] && continue
    if [[ "$line" =~ ^([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
      name="${BASH_REMATCH[1]}"
      value="${BASH_REMATCH[2]}"
      if [[ -n "$current_key" ]]; then
        export EC2_SSH_KEY="$current_key"
        current_key=""
      fi
      if [[ "$name" == "EC2_SSH_KEY" ]]; then
        current_key="$value"
      else
        export "$name=$value"
      fi
    else
      [[ -n "$current_key" ]] && current_key="$current_key"$'\n'"$line"
    fi
  done < .env
  [[ -n "$current_key" ]] && export EC2_SSH_KEY="$current_key"
fi

if [ -z "${EC2_SSH_KEY:-}" ]; then
  echo "Error: EC2_SSH_KEY is not set. Put EC2_HOST, EC2_USER, EC2_SSH_KEY, EC2_MODULE_PATH in .env"
  exit 1
fi

for var in EC2_HOST EC2_USER EC2_MODULE_PATH; do
  eval "val=\${$var:-}"
  if [ -z "$val" ]; then echo "Error: $var is not set"; exit 1; fi
done

# Check required commands (standard on macOS/Linux)
for cmd in ssh ssh-keygen; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Error: $cmd not found. Install OpenSSH (e.g. on Windows: 'Add optional feature' OpenSSH Client)."
    exit 1
  fi
done

mkdir -p ~/.ssh
# Support raw PEM or base64
if printf '%s' "$EC2_SSH_KEY" | tr -d '\r' | grep -q -e '-----BEGIN'; then
  printf '%s' "$EC2_SSH_KEY" | tr -d '\r' > "$KEY_FILE"
else
  printf '%s' "$EC2_SSH_KEY" | tr -d '\r\n\t ' | base64 -d > "$KEY_FILE" 2>/dev/null || {
    echo "Error: EC2_SSH_KEY base64 decode failed. Use raw PEM or single-line base64."
    exit 1
  }
fi
[ -n "$(tail -c1 "$KEY_FILE" 2>/dev/null)" ] && echo >> "$KEY_FILE"
if ! head -1 "$KEY_FILE" | grep -q -e '-----BEGIN'; then
  echo "Error: Key is not valid PEM (truncated or wrong base64)."
  exit 1
fi
chmod 600 "$KEY_FILE"
if ! ssh-keygen -y -f "$KEY_FILE" >/dev/null 2>&1; then
  echo "Error: Key failed to load (use key with no passphrase)."
  exit 1
fi

ssh-keyscan -H "$EC2_HOST" >> ~/.ssh/known_hosts 2>/dev/null || true
ssh -i "$KEY_FILE" \
  -o StrictHostKeyChecking=no \
  -o UserKnownHostsFile=~/.ssh/known_hosts \
  -o ConnectTimeout=30 \
  -o ServerAliveInterval=10 \
  -o ServerAliveCountMax=3 \
  "${EC2_USER}@${EC2_HOST}" \
  "MODULE_PATH='${EC2_MODULE_PATH}' bash -s" < scripts/remote-deploy.sh

echo "Local deploy finished successfully."
