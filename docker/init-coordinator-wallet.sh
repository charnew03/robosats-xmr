#!/bin/sh
set -eu

RPC_URL="${MONERO_WALLET_RPC_URL:-http://wallet-rpc:18083}"
WALLET_NAME="${MONERO_COORDINATOR_WALLET_NAME:-coordinator}"
WALLET_PASSWORD="${MONERO_COORDINATOR_WALLET_PASSWORD:-}"

echo "Waiting for wallet-rpc at ${RPC_URL}..."
for _ in $(seq 1 60); do
  if curl -sSf -X POST "${RPC_URL}/json_rpc" \
    -H "Content-Type: application/json" \
    -d '{"jsonrpc":"2.0","id":"0","method":"get_version","params":{}}' >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

echo "Creating/opening coordinator wallet: ${WALLET_NAME}"
CREATE_PAYLOAD=$(cat <<EOF
{"jsonrpc":"2.0","id":"0","method":"create_wallet","params":{"filename":"${WALLET_NAME}","password":"${WALLET_PASSWORD}","language":"English"}}
EOF
)
if ! curl -sS -X POST "${RPC_URL}/json_rpc" -H "Content-Type: application/json" -d "${CREATE_PAYLOAD}" >/dev/null; then
  OPEN_PAYLOAD=$(cat <<EOF
{"jsonrpc":"2.0","id":"0","method":"open_wallet","params":{"filename":"${WALLET_NAME}","password":"${WALLET_PASSWORD}"}}
EOF
)
  curl -sS -X POST "${RPC_URL}/json_rpc" -H "Content-Type: application/json" -d "${OPEN_PAYLOAD}" >/dev/null
fi

echo "Coordinator wallet ready."
