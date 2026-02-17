#!/usr/bin/env bash
set -euo pipefail

# Configure Linux signing secrets for GitHub Actions using an existing local GPG key.
# Usage:
#   ./installers/linux/configure_gpg_signing.sh --repo owner/repo --fingerprint <FPR> [--passphrase-env VAR]

REPO=""
FPR=""
PASSPHRASE_ENV=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)
      REPO="$2"
      shift 2
      ;;
    --fingerprint)
      FPR="$2"
      shift 2
      ;;
    --passphrase-env)
      PASSPHRASE_ENV="$2"
      shift 2
      ;;
    *)
      echo "Unknown arg: $1" >&2
      exit 1
      ;;
  esac
done

if [[ -z "$REPO" || -z "$FPR" ]]; then
  echo "Required: --repo owner/repo --fingerprint <FINGERPRINT>" >&2
  exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "gh CLI is required" >&2
  exit 1
fi

if ! command -v gpg >/dev/null 2>&1; then
  echo "gpg is required" >&2
  exit 1
fi

TMP_KEY="$(mktemp)"
trap 'rm -f "$TMP_KEY"' EXIT

gpg --armor --export-secret-keys "$FPR" | base64 > "$TMP_KEY"

echo "Setting LINUX_SIGNING_KEY_BASE64"
gh secret set LINUX_SIGNING_KEY_BASE64 --repo "$REPO" < "$TMP_KEY"

echo "Setting LINUX_SIGNING_FINGERPRINT"
printf '%s' "$FPR" | gh secret set LINUX_SIGNING_FINGERPRINT --repo "$REPO" --body -

if [[ -n "$PASSPHRASE_ENV" ]]; then
  PASS_VAL="${!PASSPHRASE_ENV:-}"
  if [[ -z "$PASS_VAL" ]]; then
    echo "Environment variable $PASSPHRASE_ENV is empty" >&2
    exit 1
  fi
  echo "Setting LINUX_SIGNING_KEY_PASSPHRASE"
  printf '%s' "$PASS_VAL" | gh secret set LINUX_SIGNING_KEY_PASSPHRASE --repo "$REPO" --body -
fi

echo "Done. Linux signing secrets configured for $REPO"
