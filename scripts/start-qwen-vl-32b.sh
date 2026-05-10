#!/usr/bin/env bash
set -euo pipefail

cd /storage/nvme3/shushanfu/MIMU-colleague

QWEN_VL_MAX_MODEL_LEN="${QWEN_VL_MAX_MODEL_LEN:-15000}"
QWEN_VL_MAX_NUM_SEQS="${QWEN_VL_MAX_NUM_SEQS:-1}"
QWEN_VL_GPU_MEMORY_UTILIZATION="${QWEN_VL_GPU_MEMORY_UTILIZATION:-0.70}"
QWEN_VL_MM_PROCESSOR_KWARGS=${QWEN_VL_MM_PROCESSOR_KWARGS:-'{"max_pixels":786432}'}

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
  --max-model-len "${QWEN_VL_MAX_MODEL_LEN}" \
  --max-num-seqs "${QWEN_VL_MAX_NUM_SEQS}" \
  --gpu-memory-utilization "${QWEN_VL_GPU_MEMORY_UTILIZATION}" \
  --enforce-eager \
  --mm-processor-kwargs "${QWEN_VL_MM_PROCESSOR_KWARGS}" \
  --limit-mm-per-prompt '{"image": 1}'
