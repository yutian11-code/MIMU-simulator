#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${ROOT_DIR:-/storage/nvme3/shushanfu/MIMU-colleague}"
CERT_DIR="${ROOT_DIR}/var/certs"
CERT_PATH="${MIMU_HTTPS_CERT:-${CERT_DIR}/mimu-lan.crt}"
KEY_PATH="${MIMU_HTTPS_KEY:-${CERT_DIR}/mimu-lan.key}"
OPENSSL_CONFIG="${CERT_DIR}/mimu-lan-openssl.cnf"
LAN_IP="${MIMU_LAN_IP:-10.246.1.70}"
LAN_DNS="${MIMU_LAN_DNS:-mimu-lan.local}"

mkdir -p "${CERT_DIR}"

if [[ ! -f "${CERT_PATH}" || ! -f "${KEY_PATH}" ]]; then
  cat > "${OPENSSL_CONFIG}" <<EOF
[req]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn
x509_extensions = v3_req

[dn]
CN = ${LAN_IP}

[v3_req]
subjectAltName = @alt_names

[alt_names]
IP.1 = ${LAN_IP}
IP.2 = 127.0.0.1
DNS.1 = localhost
DNS.2 = ${LAN_DNS}
EOF

  openssl req \
    -x509 \
    -nodes \
    -newkey rsa:2048 \
    -days 365 \
    -keyout "${KEY_PATH}" \
    -out "${CERT_PATH}" \
    -config "${OPENSSL_CONFIG}" \
    -extensions v3_req
fi

export MIMU_HTTPS_CERT="${CERT_PATH}"
export MIMU_HTTPS_KEY="${KEY_PATH}"
exec node "${ROOT_DIR}/scripts/https-lan-gateway.mjs"
