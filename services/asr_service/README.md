# MIMU ASR Service

This service provides local speech recognition for the A-version roadshow voice coach.

## Environment

Use Chinese mirrors when creating the environment:

```bash
conda create -n mimu-voice python=3.12 -y -c https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main
conda run -n mimu-voice pip install -r /storage/nvme3/shushanfu/MIMU-colleague/services/asr_service/requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

## Model Download

Download through the project checkpoint helper:

```bash
HF_ENDPOINT=https://hf-mirror.com python /storage/nvme3/shushanfu/checkpoint/down_load.py \
  --repo-id Qwen/Qwen3-ASR-0.6B \
  --save-path /storage/nvme3/shushanfu/checkpoint/huggingface/Qwen/Qwen3-ASR-0.6B
```

If the HF mirror fails, retry with the user-approved local proxy:

```bash
HF_ENDPOINT=https://hf-mirror.com \
HTTPS_PROXY=http://127.0.0.1:7890 \
HTTP_PROXY=http://127.0.0.1:7890 \
python /storage/nvme3/shushanfu/checkpoint/down_load.py \
  --repo-id Qwen/Qwen3-ASR-0.6B \
  --save-path /storage/nvme3/shushanfu/checkpoint/huggingface/Qwen/Qwen3-ASR-0.6B
```

## Start

The default model path is `/storage/nvme3/shushanfu/checkpoint/huggingface/Qwen/Qwen3-ASR-0.6B` when it exists.

```bash
tmux new-session -d -s mimu_asr_8020 \
  'CUDA_DEVICE_ORDER=PCI_BUS_ID CUDA_VISIBLE_DEVICES=1 MIMU_ASR_DEVICE=cuda:0 MIMU_ASR_LANGUAGE=Chinese conda run -n mimu-voice python /storage/nvme3/shushanfu/MIMU-colleague/services/asr_service/server.py --host 0.0.0.0 --port 8020 2>&1 | tee /storage/nvme3/shushanfu/MIMU-colleague/var/logs/asr-8020.log'
```

Backend env:

```env
COACH_ASR_BASE_URL=http://127.0.0.1:8020
COACH_ASR_TIMEOUT_MS=120000
```

## Verify

```bash
curl -fsS http://127.0.0.1:8020/health
python -m unittest services.asr_service.test_server
```
