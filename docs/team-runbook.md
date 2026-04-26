# MIMU Colleague Team Runbook

本文档记录当前同事版项目的本地运行、联调验证和后续交付缺口。旧版
`/storage/nvme3/shushanfu/MIMU` 只作为技术备份；当前有效工作目录是
`/storage/nvme3/shushanfu/MIMU-colleague`。

## 仓库与分支

- 后端：`backend`，基线 `origin/master`，开发分支 `feature-ssf`
- 前端：`frontend`，基线 `origin/dev`，开发分支 `feature-ssf`
- 妆容迁移节点：`stable-makeup`，包含本地 diffusers 兼容补丁
- ComfyUI：`ComfyUI`，作为本机推理服务使用
- 评测工具：`eval/makeup`，位于当前顶层元仓库

## 当前联调地址

- 后端健康检查：`http://10.246.1.70:13000/health`
- 前端 Expo Web：`http://10.246.1.70:19006`
- ComfyUI：`http://10.246.1.70:8188`

其他机器访问前端时，确保前端 `.env.local` 指向后端局域网地址：

```env
EXPO_PUBLIC_API_BASE_URL=http://10.246.1.70:13000
```

后端 `.env` 中 ComfyUI 地址默认是本机：

```env
COMFY_UI_BASE_URL=http://127.0.0.1:8188
```

## 验证命令

后端：

```bash
cd /storage/nvme3/shushanfu/MIMU-colleague/backend
npm run build
npm run test
npm run test:e2e
curl -fsS http://127.0.0.1:13000/health
```

前端：

```bash
cd /storage/nvme3/shushanfu/MIMU-colleague/frontend
npx tsc --noEmit
npm run lint
curl -I http://127.0.0.1:19006
```

## AI 视频指导

执行页已经接入 `AI 视频指导`。前端会把当前步骤、用户问题和一帧摄像头画面发到后端
`POST /makeup/coach`。没有模型 key 时，后端返回本地规则兜底指导，路演流程仍可跑通。

本地先用 32B AWQ 跑通：

```bash
CUDA_VISIBLE_DEVICES=0,1,2,3 vllm serve /storage/nvme3/shushanfu/checkpoint/huggingface/Qwen/Qwen2.5-VL-32B-Instruct-AWQ \
  --served-model-name Qwen/Qwen2.5-VL-32B-Instruct-AWQ \
  --host 0.0.0.0 \
  --port 8010 \
  --tensor-parallel-size 4 \
  --quantization awq \
  --dtype half \
  --max-model-len 4096 \
  --max-num-seqs 1 \
  --gpu-memory-utilization 0.85 \
  --enforce-eager
```

32B 跑通后再试 72B AWQ：

```bash
CUDA_VISIBLE_DEVICES=0,1,2,3 vllm serve /storage/nvme3/shushanfu/checkpoint/huggingface/Qwen/Qwen2.5-VL-72B-Instruct-AWQ \
  --served-model-name Qwen/Qwen2.5-VL-72B-Instruct-AWQ \
  --host 0.0.0.0 \
  --port 8010 \
  --tensor-parallel-size 4 \
  --quantization awq \
  --dtype half \
  --max-model-len 4096 \
  --max-num-seqs 1 \
  --gpu-memory-utilization 0.85 \
  --enforce-eager
```

后端接本地 vLLM：

```env
COACH_LLM_API_KEY=EMPTY
COACH_LLM_BASE_URL=http://127.0.0.1:8010/v1
COACH_LLM_MODEL=Qwen/Qwen2.5-VL-32B-Instruct-AWQ
```

后端接 DashScope：

```env
COACH_LLM_API_KEY=<DashScope 百炼 Key>
COACH_LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
COACH_LLM_MODEL=qwen-vl-plus-latest
```

模型下载：

```bash
cd /storage/nvme3/shushanfu/MIMU-colleague
bash scripts/download-qwen-vl-models.sh
```

摄像头注意事项：浏览器对局域网 HTTP 页面会限制 `getUserMedia`。本机可用
`localhost` 打开；其他机器路演时建议用 HTTPS，或在 AI 视频指导页使用“上传画面”兜底。

评测工具：

```bash
cd /storage/nvme3/shushanfu/MIMU-colleague
/home/shushanfu/software/Anaconda/envs/mimu-comfy/bin/python -m unittest discover -s eval/makeup/tests -v
/home/shushanfu/software/Anaconda/envs/mimu-comfy/bin/python eval/makeup/scripts/run_eval_pipeline.py --project-root /storage/nvme3/shushanfu/MIMU-colleague --output-root eval/makeup --backend-url http://127.0.0.1:13000 --case-count 90 --limit 90 --vlm-mode mock --run-id regression_90
```

## 人工验收路径

1. 打开 `http://10.246.1.70:19006`。
2. 使用测试账号登录：`demo@beautyasset.app` / `demo123456`。
3. 进入推荐页，选择一个彩妆模板。
4. 查看模板图片和视频是否正常显示。
5. 进入方案结果页，使用“妆容预览”上传或拍摄一张正脸图。
6. 等待生成结果，确认页面能显示 `/makeup/result` 返回的图片。
7. 如浏览器无法访问摄像头，优先改用相册上传；再检查浏览器站点权限、HTTPS/HTTP 策略和设备摄像头占用。

## 可复现补丁

Stable Makeup 的本地兼容补丁已导出到：

```text
patches/stable-makeup/0001-fix-support-current-diffusers-controlnet-import.patch
```

新机器重新拉取 `stable-makeup` 后，可按
`patches/stable-makeup/README.md` 应用并验证。

## 隐私与内测

内测照片规则见 `docs/internal-test-and-privacy.md`。默认评测使用
`--vlm-mode mock`，不会把图片发送到外部 VLM/LLM。真实人脸图片不要提交到
git，也不要放进共享报告。

清理本机测试图像和评测产物前先 dry-run：

```bash
bash scripts/cleanup-local-artifacts.sh --dry-run
```

## 还未完成的产品化工作

- 还需要在真实手机浏览器、Expo Go 或原生包中各跑一次端侧验收。
- 当前 90 case 仍是 starter regression set，只能防回归，不能代表真实产品质量。
- 仍需要补充授权真实照片或 AI 生成肖像，建立人工抽检机制。
- 单机内存队列适合当前内测；正式多机部署需要 Redis/数据库持久化队列。
