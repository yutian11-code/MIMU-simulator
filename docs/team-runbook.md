# MIMU Colleague Team Runbook

本文档记录当前项目的本地运行、联调验证和交付缺口。
旧版 `/storage/nvme3/shushanfu/MIMU` 只作为技术备份；
当前有效工作目录是
`/storage/nvme3/shushanfu/MIMU-colleague`。

## 仓库与分支

- 后端：`backend`，基线 `origin/master`，当前开发分支
  `feature-makeup-template-generation`
- 前端：`frontend`，基线 `origin/dev`，当前开发分支
  `feature-makeup-template-generation`
- 妆容迁移节点：`stable-makeup`，包含本地 diffusers 兼容补丁
- ComfyUI：`ComfyUI`，作为本机推理服务使用
- 评测工具：`eval/makeup`，位于当前顶层元仓库

## 当前联调地址

- 后端健康检查：`http://10.246.1.70:13001/health`
- 前端 Expo Web：`http://10.246.1.70:19006`
- HTTPS 路演入口：`https://10.246.1.70:19443`
- ComfyUI：`http://10.246.1.70:8188`
- 语音识别服务：`http://10.246.1.70:8020`

其他机器访问前端时，确保前端 `.env.local`
指向后端局域网地址：

```env
EXPO_PUBLIC_API_BASE_URL=http://10.246.1.70:13001
```

后端 `.env` 中 ComfyUI 地址默认是本机：

```env
COMFY_UI_BASE_URL=http://127.0.0.1:8188
```

## 上线后 P0/P1 操作

运营、产品和演示同学优先使用 HTTPS 路演入口：

```text
https://10.246.1.70:19443
```

每日开场前先跑一键健康检查：

```bash
cd /storage/nvme3/shushanfu/MIMU-colleague
scripts/check-demo-health.sh
```

需要同时覆盖推荐、模板、预览和教练 smoke 时：

```bash
scripts/check-demo-health.sh --with-smoke
```

只重启应用层服务，不动 ASR、VLM、ComfyUI：

```bash
scripts/restart-demo-services.sh --dry-run
scripts/restart-demo-services.sh
```

`--include-models` 只能在明确的模型维护窗口使用。默认重启脚本只处理
`mimu-backend-13000`、`mimu-backend-13001`、`mimu-frontend-19006` 和
`mimu-https-gateway-19443`，避免影响其他同学共用的模型服务。

实时跟妆回归：

```bash
python eval/coach/scripts/run_realtime_coach_regression.py \
  --backend-url http://127.0.0.1:13001 \
  --image-limit 4 \
  --video-limit 2 \
  --output /tmp/mimu-coach-regression.json
```

脚本会用 `eval/data/评测集` 的图片、`data/` 下的用户实测视频抽帧、
`eval/coach/assets/audio` 的语音样本和 WebSocket wake 握手覆盖链路。

常见故障第一反应：

- 页面空白：先跑 `scripts/check-demo-health.sh`，再看
  `var/logs/frontend-19006.log` 和浏览器控制台。
- 摄像头或麦克风打不开：优先走 `https://10.246.1.70:19443`，并检查证书信任、
  浏览器站点权限和设备占用；HTTP 局域网地址通常不能申请摄像头权限。
- ASR 没有转写：检查 `http://127.0.0.1:8020/health` 和
  `var/logs/asr-8020.log`；回归脚本会跳过低 RMS 的无语音样本。
- VLM token 或模型长度错误：检查 `COACH_LLM_MODEL`、`COACH_LLM_BASE_URL`、
  vLLM `--max-model-len` 和后端日志中的 `coach_step_evaluate`。
- WebSocket 连不上：检查 `/makeup/coach/realtime/wake`、HTTPS 网关 upgrade 和
  `realtime_event` 日志。
- AI 说完成但用户没确认：当前产品逻辑要求用户语音或按钮确认后才推进，
  前端会显示 `AI 已确认，等待用户确认`；唤醒模式提示
  `唤醒后再说：我完成了，下一步 / 帮我看一下`。

模板库运营按 P1/P2/P3 分层处理：P1 可直接展示和匹配，P2 可进入人工校验池，
P3 只保留来源音视频、抽帧和结构化草稿，不进入前台展示。所有模板必须保留
source media、步骤、产品位、适配人群、质量标签和人工校验状态，方便后续回滚、
复核和扩展。

## 验证命令

后端：

```bash
cd /storage/nvme3/shushanfu/MIMU-colleague/backend
npm run build
npm run test
npm run test:e2e
curl -fsS http://127.0.0.1:13001/health
```

前端：

```bash
cd /storage/nvme3/shushanfu/MIMU-colleague/frontend
npx tsc --noEmit
npm run lint
curl -I http://127.0.0.1:19006
curl -k -I https://127.0.0.1:19443
curl -k https://127.0.0.1:19443/api/health
```

HTTPS 局域网入口：

```bash
cd /storage/nvme3/shushanfu/MIMU-colleague
tmux new-session -d -s mimu_https_gateway \
  'bash -lc "bash scripts/start-https-lan-gateway.sh 2>&1 |
  tee var/logs/https-lan-gateway.log"'
```

这个网关监听 `0.0.0.0:19443`，页面请求转发到 `127.0.0.1:19006`，
`/api/*` 转发到 `127.0.0.1:13001`。前端在 HTTPS 访问时会自动使用
同源 `/api`，避免浏览器 mixed content 拦截。

## MMU 模板库智能匹配

模板匹配链路默认不独占 GPU。在线优先读取 PostgreSQL 中
`published` 的标准模板当前版本；数据库未 seed 时会回退到本地静态模板，
保证开发环境可用。正式生成路径要求 embedding 和 reranker 服务可用；
这两个服务不可用时会返回明确错误，不再静默降级为低质量规则匹配。

本地 smoke 可先启动 OpenAI-compatible mock 服务：

```bash
cd /storage/nvme3/shushanfu/MIMU-colleague
node scripts/start-template-model-mock-services.mjs
```

然后设置后端环境：

```env
TEMPLATE_EMBEDDING_BASE_URL=http://127.0.0.1:8030
TEMPLATE_EMBEDDING_MODEL=Qwen3-Embedding-4B
TEMPLATE_RERANKER_BASE_URL=http://127.0.0.1:8031
TEMPLATE_RERANKER_MODEL=Qwen3-Reranker-8B
TEMPLATE_VLM_BASE_URL=http://127.0.0.1:8032
TEMPLATE_VLM_MODEL=Qwen2.5-VL-32B-Instruct-AWQ
TEMPLATE_MODEL_TIMEOUT_MS=5000
```

生产/路演环境必须把这些变量指向真实 Qwen embedding、reranker 和 VLM
服务。排查时搜索响应里的 `templateTraceId`，后端结构化日志会带同一个 ID。

模板匹配评测可在后端启动后运行。`match-debug` 适合快速定位模板命中，
`recommendation` 会走完整推荐生成入口：

```bash
python eval/template_matching/run_template_matching_eval.py \
  --backend-url http://127.0.0.1:13001 \
  --mode match-debug \
  --output eval/template_matching/report.local.json
python eval/template_matching/run_template_matching_eval.py \
  --backend-url http://127.0.0.1:13001 \
  --mode recommendation \
  --output /tmp/mimu-template-recommendation.report.json
```

不要提交 `eval/template_matching/report*.json` 或
`eval/template_matching/*.report.json` 这类本地评测报告；这些路径已在顶层
`.gitignore` 忽略，也可直接输出到 `/tmp`。`recommendation` 模式是端到端
推荐 smoke：case 中的 `profile` 和 `ownedProducts` 只作为文本
requirements 信号发送，不会替换后端数据库里的用户资料或资产 fixture。
该模式会在响应包含 `steps[].standardStepCodes` 时检查
`requiredStepCodes`；`match-debug` 等不返回 step code 的响应会把检查标为
`skipped`。

### Platform Smoke

启动模板匹配 mock 模型服务并跑平台 smoke：

```bash
cd /storage/nvme3/shushanfu/MIMU-colleague
MIMU_MODEL_MODE=mock bash scripts/start-mimu-platform-services.sh
MIMU_BACKEND_URL=http://127.0.0.1:13001 bash scripts/smoke-mimu-platform.sh
```

`scripts/start-mimu-platform-services.sh` 在 mock 模式下会启动
embedding、rerank 和参考图 VLM mock 服务，端口为 `8030/8031/8032`，
日志写入 `var/logs/template-model-mocks.log`。真实模型模式下不要使用
mock，需按本 runbook 配置真实 embedding、rerank、VLM、ASR、ComfyUI 和
coach 服务。

平台健康检查：

```bash
curl -fsS http://127.0.0.1:13001/platform/health | python -m json.tool
```

重点看：

- `models.templateEmbedding`
- `models.templateReranker`
- `models.referenceVlm`
- `models.asr`
- `models.coach`
- `models.comfyui`

排查日志时优先搜索：

- `templateTraceId`：模板匹配和推荐生成。
- `preview_`：妆容预览任务。
- `coach_`：图片/实时跟妆步骤评估。
- `voice_`：语音转写和语音教练。

smoke 脚本会依次验证后端健康、平台健康、模板库 seed、推荐生成、预览
job 创建、静态图片 step-evaluate schema、模板匹配评测，并把 JSON 结果写到
`/tmp/mimu-*.json`。

### 模板库初始化与管理

首次部署或数据库迁移后，先执行迁移：

```bash
cd /storage/nvme3/shushanfu/MIMU-colleague/backend
npx prisma migrate deploy
```

然后 seed 产品文档中的标准模板库：

```bash
curl -fsS -X POST http://127.0.0.1:13001/makeup-template-library/seed \
  -H 'Authorization: Bearer demo-token' \
  -H 'Content-Type: application/json' \
  -d '{}' | python -m json.tool
```

预期返回 8 个 style/template 计数，以及产品分类、操作区域、脸型和难度规则计数。

管理 API：

```text
GET  /makeup-template-library/taxonomy
GET  /makeup-template-library/templates
GET  /makeup-template-library/templates/:templateId
GET  /makeup-template-library/templates/:templateId/versions
GET  /makeup-template-library/templates/:templateId/versions/:versionId
POST /makeup-template-library/templates
PUT  /makeup-template-library/templates/:templateId/draft
POST /makeup-template-library/templates/:templateId/publish
POST /makeup-template-library/templates/:templateId/archive
POST /makeup-template-library/templates/:templateId/rollback
POST /makeup-template-library/seed
```

前端入口：

```text
个人档案 -> 模板库管理
```

前端可完成：

- 导入标准模板。
- 按状态搜索模板。
- 编辑当前版本生成草稿。
- 发布草稿为当前正式版本。
- 查看版本历史并回滚，回滚会复制历史版本生成新的已发布版本。

推荐链路验证：

```bash
curl -fsS -X POST http://127.0.0.1:13001/recommendations/generate \
  -H 'Authorization: Bearer demo-token' \
  -H 'Content-Type: application/json' \
  -d '{"userId":"user-001","scenario":"面试","scenarioDetails":"面试需要轻熟知性优雅妆，不要太浓","requirements":["不要太浓"]}' \
  | python -m json.tool
```

响应应包含：

- `generatedTemplateId`
- `sourceStandardTemplateId`
- `sourceStandardTemplateVersionId`
- `templateFamily`
- `matchScore`
- `steps[].productSlots`

资源预算：

- GPU 0-3：3090，可承载轻量 embedding、reranker 或离线批处理。
- GPU 4-7：48G 4090，保留给 VLM、妆容预览和实时教练。
- 该路径不新增常驻 72B 服务。

后端必需环境变量：

```env
TEMPLATE_EMBEDDING_BASE_URL=http://127.0.0.1:8030/v1
TEMPLATE_EMBEDDING_MODEL=Qwen3-Embedding-4B
TEMPLATE_RERANKER_BASE_URL=http://127.0.0.1:8031/v1
TEMPLATE_RERANKER_MODEL=Qwen3-Reranker-8B
TEMPLATE_VLM_BASE_URL=http://127.0.0.1:8010/v1
TEMPLATE_VLM_MODEL=Qwen2.5-VL-32B-Instruct-AWQ
TEMPLATE_MODEL_TIMEOUT_MS=5000
```

模型下载优先使用 hf-mirror：

```bash
HF_ENDPOINT=https://hf-mirror.com \
python /storage/nvme3/shushanfu/checkpoint/down_load.py ...
```

如果镜像下载失败，再按需加 7890 端口代理。

## AI 视频指导

执行页已接入 `AI 视频指导`。前端会把步骤、问题和一帧
摄像头画面发到后端 `POST /makeup/coach`。没有模型 key 时，
后端返回
本地规则兜底指导，路演流程仍可跑通。

本地先用 32B AWQ 跑通。启动脚本默认使用 4 张 4090
（GPU 3,4,5,6）和
`tensor-parallel-size=4`：

```bash
tmux new-session -d -s mimu_qwen_vl_32b \
  'bash -lc "bash scripts/start-qwen-vl-32b.sh 2>&1 |
  tee var/logs/qwen-vl-32b-vllm.log"'
```

32B 跑通后再试 72B AWQ：

```bash
MODEL_DIR=/storage/nvme3/shushanfu/checkpoint/huggingface/Qwen
CUDA_VISIBLE_DEVICES=3,4,5,6 vllm serve \
  "$MODEL_DIR/Qwen2.5-VL-72B-Instruct-AWQ" \
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
COACH_LLM_TIMEOUT_MS=120000
COACH_ASR_BASE_URL=http://127.0.0.1:8020
COACH_ASR_TIMEOUT_MS=120000
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

### A 版语音指导

A 版语音指导是“录音 -> ASR 转写 -> 当前画面 + 文本进入
32B 视觉教练 -> 浏览器播报结果”的短轮次方案。
它不是连续监听；
连续视频通话和低延迟流式 ASR 留到 B 版。

ASR 使用 `Qwen/Qwen3-ASR-0.6B`。Qwen 官方模型卡说明该系列支持
离线和流式识别，`qwen-asr` 包可接收本地路径、URL、base64 或
numpy 音频输入。本项目 A 版把浏览器音频转为 WAV data URL，
再在 Python 服务中写成临时 WAV 文件转写。

创建语音环境和安装依赖：

```bash
conda create -n mimu-voice python=3.12 -y \
  -c https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main
conda run -n mimu-voice pip install \
  -r services/asr_service/requirements.txt \
  -i https://pypi.tuna.tsinghua.edu.cn/simple
```

下载 ASR 模型：

```bash
MODEL_DIR=/storage/nvme3/shushanfu/checkpoint/huggingface/Qwen
HF_ENDPOINT=https://hf-mirror.com \
python /storage/nvme3/shushanfu/checkpoint/down_load.py \
  --repo-id Qwen/Qwen3-ASR-0.6B \
  --save-path "$MODEL_DIR/Qwen3-ASR-0.6B"
```

如果 hf-mirror 下载失败，再使用你允许的 7890 端口代理：

```bash
MODEL_DIR=/storage/nvme3/shushanfu/checkpoint/huggingface/Qwen
HF_ENDPOINT=https://hf-mirror.com \
HTTPS_PROXY=http://127.0.0.1:7890 \
HTTP_PROXY=http://127.0.0.1:7890 \
python /storage/nvme3/shushanfu/checkpoint/down_load.py \
  --repo-id Qwen/Qwen3-ASR-0.6B \
  --save-path "$MODEL_DIR/Qwen3-ASR-0.6B"
```

启动本地 ASR：

```bash
tmux new-session -d -s mimu_asr_8020 \
  'CUDA_DEVICE_ORDER=PCI_BUS_ID CUDA_VISIBLE_DEVICES=1 MIMU_ASR_DEVICE=cuda:0 \
  MIMU_ASR_LANGUAGE=Chinese conda run -n mimu-voice python \
  services/asr_service/server.py --host 0.0.0.0 --port 8020 \
  2>&1 | tee var/logs/asr-8020.log'
```

检查：

```bash
curl -fsS http://127.0.0.1:8020/health
```

摄像头权限排查：

- `http://10.246.1.70:19006` 这种局域网 HTTP 可做页面演示和
  上传图片，但浏览器会禁用摄像头。
- 路演摄像头优先打开 `https://10.246.1.70:19443`。
- 首次打开会看到自签名证书警告，点击高级/继续；
  如果浏览器
  仍然
  不允许摄像头，需要把
  `/storage/nvme3/shushanfu/MIMU-colleague/var/certs/mimu-lan.crt`
  导入测试电脑的系统信任证书。
- 在服务器本机浏览器打开 `http://localhost:19006`
  可以申请摄像头权限。
- 其他机器要使用摄像头，需要可信 HTTPS 域名，或在 Chrome 的
  `chrome://flags/#unsafely-treat-insecure-origin-as-secure` 中临时加入
  `http://10.246.1.70:19006`，重启浏览器后再测试。
- 不改浏览器设置时，路演可用 `上传画面`，
  上传帧会进入同一个
  32B VLM 指导链路。

评测工具：

```bash
cd /storage/nvme3/shushanfu/MIMU-colleague
/home/shushanfu/software/Anaconda/envs/mimu-comfy/bin/python \
  -m unittest discover -s eval/makeup/tests -v
/home/shushanfu/software/Anaconda/envs/mimu-comfy/bin/python \
  eval/makeup/scripts/run_eval_pipeline.py \
  --project-root /storage/nvme3/shushanfu/MIMU-colleague \
  --output-root eval/makeup \
  --backend-url http://127.0.0.1:13001 \
  --case-count 90 \
  --limit 90 \
  --vlm-mode mock \
  --run-id regression_90
```

## 人工验收路径

1. 打开 `http://10.246.1.70:19006`。
2. 使用测试账号登录：`demo@beautyasset.app` / `demo123456`。
3. 进入推荐页，选择一个彩妆模板。
4. 查看模板图片和视频是否正常显示。
5. 进入方案结果页，使用“妆容预览”上传或拍摄正脸图。
6. 等待结果，确认页面能显示 `/makeup/result` 返回的图片。
7. 如浏览器无法访问摄像头，优先改用相册上传；再检查
   站点权限、
   HTTPS/HTTP 策略和设备摄像头占用。

## 可复现补丁

Stable Makeup 的本地兼容补丁已导出到：

```text
patches/stable-makeup/0001-fix-support-current-diffusers-controlnet-import.patch
```

新机器重新拉取 `stable-makeup` 后，可按
`patches/stable-makeup/README.md` 应用并验证。

## 隐私与内测

内测照片规则见 `docs/internal-test-and-privacy.md`。默认评测使用
`--vlm-mode mock`，不会把图片发送到外部 VLM/LLM。
真实人脸图片不要提交到
git，也不要放进共享报告。

清理本机测试图像和评测产物前先 dry-run：

```bash
bash scripts/cleanup-local-artifacts.sh --dry-run
```

## 还未完成的产品化工作

- 还需要在真实手机浏览器、Expo Go 或原生包中做端侧验收。
- 当前 90 case 仍是 starter regression set，只能防回归，
  不能代表真实产品质量。
- 仍需要补充授权真实照片或 AI 生成肖像，建立抽检机制。
- 单机内存队列适合当前内测；正式多机部署需要 Redis
  或数据库持久化队列。
