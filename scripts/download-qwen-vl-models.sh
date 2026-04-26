#!/usr/bin/env bash
set -euo pipefail

LOG_DIR="/storage/nvme3/shushanfu/MIMU-colleague/var/logs"
DOWNLOADER="/storage/nvme3/shushanfu/checkpoint/down_load.py"

mkdir -p "${LOG_DIR}"

export DOWNLOAD_PROFILE="qwen-vl"
export HF_DOWNLOAD_THREADS="${HF_DOWNLOAD_THREADS:-16}"
export HF_DOWNLOAD_MAX_RETRIES="${HF_DOWNLOAD_MAX_RETRIES:-3}"

export HF_ENDPOINT="https://hf-mirror.com"
python "${DOWNLOADER}" --profile qwen-vl 2>&1 | tee "${LOG_DIR}/qwen-vl-download-hf-mirror.log" || {
  export HTTP_PROXY="http://127.0.0.1:7890"
  export HTTPS_PROXY="http://127.0.0.1:7890"
  export ALL_PROXY="socks5://127.0.0.1:7890"
  python "${DOWNLOADER}" --profile qwen-vl 2>&1 | tee "${LOG_DIR}/qwen-vl-download-proxy-7890.log"
}
