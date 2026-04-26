#!/usr/bin/env bash
set -euo pipefail

cd /storage/nvme3/shushanfu/MIMU-colleague

CUDA_DEVICE_ORDER=PCI_BUS_ID \
CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-3,4,5,6}" \
/home/shushanfu/software/Anaconda/envs/fastchat/bin/python -m vllm.entrypoints.openai.api_server \
  --model /storage/nvme3/shushanfu/checkpoint/huggingface/Qwen/Qwen2.5-VL-32B-Instruct-AWQ \
  --served-model-name Qwen/Qwen2.5-VL-32B-Instruct-AWQ \
  --host 0.0.0.0 \
  --port "${QWEN_VL_PORT:-8010}" \
  --trust-remote-code \
  --tensor-parallel-size "${QWEN_VL_TENSOR_PARALLEL_SIZE:-4}" \
  --quantization awq \
  --dtype half \
  --max-model-len 4096 \
  --max-num-seqs 1 \
  --gpu-memory-utilization "${QWEN_VL_GPU_MEMORY_UTILIZATION:-0.70}" \
  --enforce-eager \
  --limit-mm-per-prompt '{"image": 1}'
