# Linux AppImage GPG Signing Setup

This project supports optional Linux signing with your own GPG key.

## 1) Generate a signing key (local machine)

```bash
gpg --full-generate-key
```

Recommended values:

- Key type: `RSA and RSA`
- Key size: `4096`
- Expiration: choose your policy
- Real name: `SmartScreen Release`
- Email: your release email

## 2) Find your key fingerprint

```bash
gpg --list-secret-keys --keyid-format LONG
```

Copy the full fingerprint (40 hex chars).

## 3) Export private key as base64 (for GitHub secret)

```bash
gpg --armor --export-secret-keys <FINGERPRINT> | base64 > linux_signing_key_base64.txt
```

On macOS (BSD base64), if needed:

```bash
gpg --armor --export-secret-keys <FINGERPRINT> | base64 > linux_signing_key_base64.txt
```

Then copy the contents of `linux_signing_key_base64.txt`.

## 4) Add GitHub secrets

Repository secrets used by this project:

- `LINUX_SIGNING_KEY_BASE64` (required for Linux signing)
- `LINUX_SIGNING_FINGERPRINT` (optional, recommended)
- `LINUX_SIGNING_KEY_PASSPHRASE` (optional, only if your key is passphrase-protected)

Using GitHub CLI:

```bash
gh secret set LINUX_SIGNING_KEY_BASE64 < linux_signing_key_base64.txt
gh secret set LINUX_SIGNING_FINGERPRINT
# optionally:
gh secret set LINUX_SIGNING_KEY_PASSPHRASE
```

Or use the helper script in this repo:

```bash
./installers/linux/configure_gpg_signing.sh --repo devodan69/smartscreen --fingerprint <FINGERPRINT>
```

Or set them in GitHub UI:

`Repo -> Settings -> Secrets and variables -> Actions`.

## 5) Validate signing in workflow

Trigger a tag build and check for `.sig` files beside AppImage artifacts.

In Linux build logs, verification step should succeed:

```bash
gpg --verify <artifact>.sig <artifact>.AppImage
```

## Notes

- If Linux secrets are not configured, release still works in free-first mode and publishes unsigned Linux artifacts.
- Never share your private key outside trusted secret storage.
