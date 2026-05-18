#!/usr/bin/env bash
# Write the master key into Vault KV v2 at secret/data/vcapp/master.
# Idempotent: overwrites with the value currently in .env's KMS_MOCK_KEY
# so dev-vault and mock mode produce the same DEKs (allows migrating
# recordings between modes without re-encryption).
set -euo pipefail

: "${VAULT_ADDR:=http://localhost:8200}"
: "${VAULT_TOKEN:=vcapp-dev-root}"
: "${KMS_MOCK_KEY:=ZGV2LWtleS0zMi1ieXRlcy1tdXN0LWJlLWxvbmctZW5vdWdoLW9rPT0=}"

export VAULT_ADDR VAULT_TOKEN

command -v vault >/dev/null || {
    echo "vault CLI not found locally — using docker..."
    docker run --rm --network=host -e VAULT_ADDR -e VAULT_TOKEN hashicorp/vault:1.18.3 \
        kv put -mount=secret vcapp/master key="$KMS_MOCK_KEY"
    exit $?
}

vault kv put -mount=secret vcapp/master key="$KMS_MOCK_KEY"
echo "wrote secret/data/vcapp/master"
