# MIMU 项目速览

> 本文件由 Codex 于 2026-05-09 通读当前工作区后整理，供后续开发者或自动化 Agent 快速接手。当前目录是 `D:\Project\MyMakeUpv0.1\MIMU`。

## 1. 项目定位

MIMU 是一个美妆路演/内测集成工作区，核心目标是把「美妆资产管理 App」「后端 API」「本地妆容迁移」「AI 视频/语音教练」「回归评测」放到同一个本地环境里联调。

主要产品链路：

- 用户使用 demo 账号登录并完成基础资料。
- 录入护肤/彩妆资产，支持搜索、拍照识别 mock、手动添加和产品生命周期管理。
- 根据场景生成推荐方案，推荐会考虑用户已有产品、缺失步骤、替代品和 halal 状态。
- 用户按步骤执行推荐，可记录进度、替换产品、提交反馈。
- 用户可把执行结果发布到社区内容流。
- 妆容预览通过后端转发图片到 ComfyUI / Stable Makeup 工作流。
- AI 视频/语音指导通过后端的 VLM/LLM、ASR 服务和 WebSocket/HTTP 接口辅助执行步骤。

## 2. 仓库结构

顶层仓库是集成仓库，`backend/` 和 `frontend/` 是独立 Git 仓库，并在顶层 `.gitignore` 中被忽略。

```text
MIMU/
  README.md                         集成仓库说明
  AGENTS.md                         本文件
  pull.sh                           拉取/更新 backend 与 frontend 的脚本
  docs/                             路演 runbook、隐私规则、技术计划与设计文档
  eval/makeup/                      妆容迁移回归评测集与 Python 评测流水线
  scripts/                          HTTPS LAN 网关、模型下载、本地清理等脚本
  services/asr_service/             本地 Qwen3-ASR FastAPI 服务
  patches/stable-makeup/            Stable Makeup 本地兼容补丁
  backend/                          NestJS 后端，独立 Git 仓库
  frontend/                         Expo / React Native 前端，独立 Git 仓库
```

不要把模型权重、ComfyUI 输入输出、真实人脸图片、评测运行产物、日志、截图、音频文件提交到 Git。

## 3. 当前 Git 状态摘要

- 顶层仓库：`AGENTS.md` 和大量本地截图、窗口 XML、日志、音频是未跟踪文件。
- `backend/`：当前扫描时工作区干净；远端是 `https://github.com/GreFir/mymakeup-backend.git`；本地当前分支显示为 `free-excute`。
- `frontend/`：远端是 `https://github.com/GreFir/my-make-up.git`；本地当前分支显示为 `main`；当前有未提交修改：
  - `app.json`
  - `app/recommendation/live-coach.native.tsx`
  - `package.json`
  - `package-lock.json`
  - `services/makeupCoachService.ts`
  - `store/demo-store.ts`
  - 另有 `voice-metro.codex*.log` 未跟踪日志
- 顶层 `pull.sh` 和 README 仍写着拉取 `backend`、`frontend` 的 `feature-ssf` 分支。实际操作前请先确认当前本地分支，不要直接覆盖用户改动。

## 4. 运行入口与端口

路演入口按文档约定为：

```text
https://10.246.1.70:19443
```

常用服务端口：

| 服务 | 默认/约定地址 |
| --- | --- |
| 前端 Expo Web | `http://0.0.0.0:19006` |
| 后端 NestJS | `http://0.0.0.0:13000`，后端 `.env.example` 默认 `3000` |
| HTTPS LAN 网关 | `https://0.0.0.0:19443` |
| ASR 服务 | `http://0.0.0.0:8020` |
| Qwen-VL vLLM | `http://0.0.0.0:8010` |
| ComfyUI | `http://0.0.0.0:8188` |
| PostgreSQL | `localhost:5432` |

前端在 HTTPS 页面下会优先走同源 `/api`，由 LAN 网关转发到后端，避免浏览器 mixed content 问题。

## 5. 后端概览

位置：`backend/`

技术栈：

- NestJS 11
- TypeScript
- Prisma 7
- PostgreSQL
- Swagger / OpenAPI
- Axios、FormData、ws
- Jest

启动相关命令：

```bash
cd backend
npm install
Copy-Item .env.example .env
npm run prisma:generate
npm run db:migrate
npm run db:seed
npm run start:dev
```

PostgreSQL 可用后端目录下的 `docker-compose.yml` 启动：

```bash
cd backend
docker compose up -d postgres
```

验证命令：

```bash
cd backend
npm run build
npm run test
npm run test:e2e
curl -fsS http://127.0.0.1:13000/health
```

### 5.1 后端模块

`backend/src/app.module.ts` 当前导入这些模块：

- `AuthModule`
- `UsersModule`
- `ProductsModule`
- `UserProductsModule`
- `RecommendationsModule`
- `ExecutionsModule`
- `PostsModule`
- `NotificationsModule`
- `DashboardModule`
- `MakeupModule`
- `PrismaModule`

`backend/src/main.ts` 做了这些全局配置：

- 读取 `.env`
- 可选 HTTPS，自签名证书会包含本机 LAN IPv4
- `configureRequestBodyLimit(app)`
- `app.enableCors()`
- `ValidationPipe`，启用 `whitelist`、`transform`、`forbidNonWhitelisted`
- 全局 `HttpExceptionFilter`
- Swagger 路径 `/docs`
- 手动把 `MakeupRealtimeGateway` 挂到 HTTP server

### 5.2 后端主要接口

认证与用户：

- `POST /auth/login`
- `GET /users/me`
- `PUT /users/me`
- `GET /users/me/settings`
- `PUT /users/me/settings`

产品与用户资产：

- `GET /products/search`
- `POST /products/recognize`
- `GET /products/:id`
- `GET /user-products`
- `GET /user-products/:id`
- `POST /user-products`
- `PUT /user-products/:id`

推荐、执行、社区：

- `POST /recommendations/generate`
- `GET /recommendations/history`
- `GET /recommendations/:id`
- `POST /executions`
- `PUT /executions/:id/progress`
- `POST /executions/:id/feedback`
- `GET /executions/history`
- `GET /posts`
- `POST /posts`
- `GET /posts/:id`
- `POST /posts/:id/like`
- `POST /posts/:id/favorite`
- `GET /users/me/posts`

提醒与仪表盘：

- `GET /notifications`
- `GET /dashboard/summary`
- `GET /health`

妆容预览与 AI 教练：

- `POST /makeup`
- `POST /makeup/jobs`
- `GET /makeup/jobs`
- `GET /makeup/jobs/:jobId`
- `GET /makeup/result`
- `POST /makeup/coach`
- `POST /makeup/coach/voice`
- WebSocket `/makeup/coach/realtime`

注意：前端当前有调用 `/user-products/:id/usage-profile` 和 `/posts/:id/comments` 的代码，但本次扫描后端 controller 时没有看到对应接口。做相关功能前需要补齐后端或调整前端。

### 5.3 数据模型

Prisma schema 位置：`backend/prisma/schema.prisma`

主要表/模型：

- `User`
- `UserSettings`
- `Product`
- `UserProduct`
- `RecommendationTemplate`
- `RecommendationTemplateStep`
- `Recommendation`
- `RecommendationStep`
- `Execution`
- `Post`

主要枚举：

- `ProductCategory`: `skincare`、`makeup`
- `ProductHalalStatus`: `certified`、`not_halal`、`unknown`
- `UserProductStatus`: `active`、`idle`、`expired`、`finished`
- `RecommendationHalalStatus`: `halal_friendly`、`mixed`、`not_recommended`、`unknown`
- `ExecutionStatus`: `draft`、`completed`、`abandoned`

### 5.4 后端环境变量重点

后端示例文件：`backend/.env.example`

重点变量：

- `HOST`、`PORT`
- `REQUEST_BODY_LIMIT`
- `DATABASE_URL`
- `DEMO_USER_ID`
- `DEMO_TOKEN`
- `COMFY_UI_BASE_URL`
- `MAKEUP_QUEUE_CONCURRENCY`
- `MAKEUP_JOB_MAX_RETRIES`
- `MAKEUP_JOB_RETRY_DELAY_MS`
- `MAKEUP_JOB_RETENTION_MS`
- `MAKEUP_JOB_SYNC_TIMEOUT_MS`
- `RECOMMENDATION_LLM_*`
- `COACH_LLM_*`
- `COACH_ASR_BASE_URL`
- `COACH_ASR_TIMEOUT_MS`
- `OPENROUTER_*`
- `DASHSCOPE_API_KEY`

demo 登录只支持 `loginType: "test"`，后端用 `DEMO_TOKEN` 做 Bearer token 校验，默认用户为 `user-001`。

### 5.5 妆容预览链路

后端 `MakeupService` 会：

1. 接收 `userImage` 和 `templateImage`。
2. 上传到 ComfyUI `/upload/image`。
3. 构造 Stable Makeup workflow。
4. 调用 ComfyUI `/prompt`。
5. 轮询 `/history/:prompt_id`。
6. 将结果通过后端 `/makeup/result` 代理返回。

`/makeup/jobs` 是异步任务接口，任务队列在内存中，适合当前内测和路演，不适合正式多机持久化部署。

### 5.6 AI 教练链路

- `POST /makeup/coach`：接收当前步骤、用户问题和可选截图，调用 OpenAI-compatible VLM/LLM；未配置模型时返回 scripted fallback。
- `POST /makeup/coach/voice`：先调用 ASR `/transcribe`，再把转写文本送入 AI 教练。
- `WebSocket /makeup/coach/realtime`：接收 `start`、`frame`、`audio_chunk`、`stop` 消息；服务端按音量 RMS 做简单 VAD，拼接 PCM16 为 WAV data URL，再复用语音教练链路。

## 6. 前端概览

位置：`frontend/`

技术栈：

- Expo 54
- React Native 0.81
- React 19
- TypeScript
- Expo Router 6
- React Navigation
- TanStack Query
- Zustand
- NativeWind / Tailwind
- Expo Camera/Image Picker/Speech/Video
- react-native-vision-camera
- Android 原生录音模块 `MimuVoiceRecorder`

启动命令：

```bash
cd frontend
npm install
npm start
```

其他常用命令：

```bash
npm run android
npm run ios
npm run web
npm run export:web:ssf
npm run lint
npx tsc --noEmit
```

### 6.1 前端路由

主要路由位于 `frontend/app/`：

- `(auth)/login`
- `(auth)/profile-setup`
- `(tabs)/index`
- `(tabs)/assets`
- `(tabs)/recommend`
- `(tabs)/community`
- `(tabs)/profile`
- `assets/search`
- `assets/recognize`
- `assets/capture`
- `assets/pick`
- `assets/manual-add`
- `assets/intake-result`
- `assets/skincare`
- `assets/makeup`
- `assets/detail`
- `recommendation/scenario`
- `recommendation/quick`
- `recommendation/products`
- `recommendation/loading`
- `recommendation/result`
- `recommendation/preview`
- `recommendation/execution`
- `recommendation/feedback`
- `recommendation/history`
- `recommendation/resume`
- `recommendation/coach`
- `recommendation/live-coach`
- `community/create`
- `community/my-posts`
- `community/[postId]`
- `utility/notifications`
- `utility/settings`

根布局 `frontend/app/_layout.tsx` 使用 `AppProviders` 包裹全局 QueryClient、Navigation theme、SafeArea、GestureHandler 和语言切换。

### 6.2 前端状态与服务层

全局状态：

- `frontend/store/demo-store.ts`
- 使用 Zustand persist 保存登录 token、当前用户、执行草稿、推荐场景、通知设置和语言。
- rehydrate 时会把 token 同步到 `api-client` 的内存 auth token。

API 配置：

- `frontend/constants/api.ts`
- 默认 fallback 是 `http://127.0.0.1:13000`。
- 如果网页在 HTTPS origin 下运行，且未显式配置 HTTPS API，会使用同源 `/api`。
- `MEDIA_CONFIG` 会尽量与 API base URL 或 HTTPS origin 对齐。

服务层：

- `services/api-client.ts`：统一 `fetch`、query 拼接、Bearer token、错误信息归一。
- `authService.ts`：登录、当前用户、设置。
- `productService.ts`：产品搜索、识别 mock、详情。
- `userProductService.ts`：用户资产。
- `recommendationService.ts`：推荐生成，后端不可用时可回退本地规则。
- `executionService.ts`：执行记录与反馈。
- `communityService.ts`：社区 feed、发帖、点赞、收藏。
- `notificationService.ts`：提醒与 dashboard summary。
- `virtualTryOnService.ts`：妆容预览 multipart 上传、异步任务轮询、结果 URL 归一。
- `makeupCoachService.ts`：视频/语音教练 HTTP 请求，可通过 `EXPO_PUBLIC_MODEL_BASE_URL` 指向单独模型服务。
- `makeupCoachRealtimeService.ts`：构造 WS/WSS 地址并发送实时消息。

### 6.3 前端 UI 与主题

主要 UI 组件在：

- `components/demo/`
- `components/ui/`
- `components/assets/`
- `components/community/`
- `components/recommendation/`
- `components/product/`

主题相关：

- `theme/beauty-theme.ts`
- `theme/dopamine-ui.ts`
- `theme/navigation-theme.ts`
- `tailwind.config.js`

Tailwind 色板偏美妆产品风格，包含 rose、lilac、mint、surface、ink、success、danger 等语义色。

### 6.4 Android 原生录音模块

当前本地 `frontend/android/` 目录存在原生 Android 代码：

- `MimuVoiceRecorderModule.kt`
- `MimuVoiceRecorderPackage.kt`
- `MainApplication.kt` 手动 `add(MimuVoiceRecorderPackage())`

模块名是 `MimuVoiceRecorder`，提供：

- `start(): Promise<string>`
- `stop(): Promise<string>`
- `cancel(): Promise<void>`

实现方式是 Android `AudioRecord`，录制 16kHz mono PCM16 WAV 到 cache 目录。这个目录看起来不是 frontend Git 已跟踪内容，处理时要特别确认是否为本地生成/预构建产物。

### 6.5 前端配置注意

- `frontend/app.json` 当前配置了 camera、microphone 权限，Android 开启 `usesCleartextTraffic`。
- `EXPO_PUBLIC_API_BASE_URL` 可在 `.env.local` 覆盖。
- `EXPO_PUBLIC_MODEL_BASE_URL` 可让语音教练请求走独立模型服务。
- 当前多个源码文件的中文在终端输出里出现乱码，修改中文文案前请确认文件实际编码，避免把乱码继续扩散。

## 7. ASR 服务

位置：`services/asr_service/`

技术栈：

- FastAPI
- Uvicorn
- Pydantic
- PyTorch
- `qwen-asr`

接口：

- `GET /health`
- `POST /transcribe`

`POST /transcribe` 输入 `audioDataUrl`，服务会解析 base64 音频，写入临时文件，调用 `Qwen3ASRModel.transcribe`，返回转写文本、provider、model 和 language。

默认模型路径：

```text
/storage/nvme3/shushanfu/checkpoint/huggingface/Qwen/Qwen3-ASR-0.6B
```

可用环境变量：

- `MIMU_ASR_MODEL`
- `MIMU_ASR_DEVICE`
- `MIMU_ASR_LANGUAGE`
- `MIMU_ASR_DTYPE`
- `MIMU_ASR_MAX_BATCH`
- `MIMU_ASR_MAX_NEW_TOKENS`
- `MIMU_ASR_HOST`
- `MIMU_ASR_PORT`

启动参考：

```bash
conda run -n mimu-voice python services/asr_service/server.py --host 0.0.0.0 --port 8020
```

测试：

```bash
python -m unittest services.asr_service.test_server
curl -fsS http://127.0.0.1:8020/health
```

## 8. 评测工具

位置：`eval/makeup/`

用途：

- 调用后端 `/makeup` API。
- 用固定用户图和模板图构建 smoke/regression case。
- 生成 deterministic auto score。
- 在 `--vlm-mode mock` 下生成 mock VLM 分数。
- 输出静态 HTML report。

常用命令：

```bash
python eval/makeup/scripts/run_eval_pipeline.py \
  --project-root . \
  --backend-url http://127.0.0.1:13000 \
  --limit 2 \
  --vlm-mode mock
```

完整 starter regression：

```bash
python eval/makeup/scripts/run_eval_pipeline.py \
  --project-root . \
  --backend-url http://127.0.0.1:13000 \
  --case-count 90 \
  --limit 90 \
  --vlm-mode mock
```

输出目录是 `eval/makeup/runs/`，已被顶层 `.gitignore` 忽略。

## 9. 顶层脚本

- `pull.sh`
  - 克隆或更新 `backend` 和 `frontend`。
  - 如果子仓库有未提交改动会拒绝继续。
  - 当前脚本目标分支写死为 `feature-ssf`。

- `scripts/https-lan-gateway.mjs`
  - 启动 HTTPS 反向代理。
  - 普通页面请求转发到 `MIMU_FRONTEND_ORIGIN`，默认 `http://127.0.0.1:19006`。
  - `/api/*` 转发到 `MIMU_BACKEND_ORIGIN`，默认 `http://127.0.0.1:13000`。
  - 支持 WebSocket upgrade。

- `scripts/start-https-lan-gateway.sh`
  - 生成本地自签名证书。
  - 默认 LAN IP 是 `10.246.1.70`。
  - 执行 Node HTTPS 网关。

- `scripts/download-qwen-vl-models.sh`
  - 下载 Qwen-VL 模型。

- `scripts/start-qwen-vl-32b.sh`
  - 启动本地 Qwen2.5-VL 32B AWQ vLLM。

- `scripts/cleanup-local-artifacts.sh`
  - 清理 ComfyUI input/output 和评测 runs。
  - 默认 `--dry-run`，确认后才用 `--apply`。

## 10. 隐私与数据规则

项目会处理人脸图像，默认按敏感数据处理。

允许用于测试的图片：

- 项目内生成的 AI 肖像。
- 许可证允许本地模型测试的公开 demo 图。
- 明确授权用于内测的真人照片。
- `eval/makeup/assets/` 中的固定回归图。

禁止提交：

- 原始用户上传。
- 真人测试照片。
- ComfyUI 输入/输出。
- `eval/makeup/runs/`。
- 含真人脸的浏览器截图。
- 模型权重和大体积生成产物。

外部模型规则：

- 未经明确批准，不要把真实人脸图发给外部 VLM/LLM/评分/分析/日志服务。
- 当前评测默认 `--vlm-mode mock`，不会把图片发出本机。

## 11. 开发注意事项

- 先确认是在顶层集成仓库、`backend/` 子仓库还是 `frontend/` 子仓库中操作。
- 不要在未确认的情况下运行 `pull.sh`，因为当前子仓库本地分支与脚本文档分支不完全一致。
- 不要覆盖 frontend 当前未提交修改。
- 后端默认端口文档存在 `3000` 与路演 `13000` 两种约定；联调优先看 `.env` 和当前运行日志。
- 前端 `.env.example` 写的是 `127.0.0.1:3000`，但 `constants/api.ts` fallback 是 `127.0.0.1:13000`。
- 修改 API 时，同时检查后端 controller、前端 service、类型定义和相关页面。
- 修改妆容预览时，同时检查 `backend/src/makeup/*`、`frontend/services/virtualTryOnService.ts`、ComfyUI 是否运行。
- 修改 AI 教练时，同时检查后端 `makeup-coach`、`makeup-voice`、`makeup-realtime`、前端 `makeupCoachService`、`makeupCoachRealtimeService`、`app/recommendation/coach*`、`live-coach*`。
- 修改语音链路时，同时检查 ASR 服务、后端 `COACH_ASR_BASE_URL`、前端 native recorder / browser recorder 入口。
- 修改中文文案时注意编码，当前终端读取部分中文文件会显示乱码。

## 12. 建议验证清单

后端：

```bash
cd backend
npm run build
npm run test
npm run test:e2e
curl -fsS http://127.0.0.1:13000/health
```

前端：

```bash
cd frontend
npx tsc --noEmit
npm run lint
curl -I http://127.0.0.1:19006
```

HTTPS 网关：

```bash
curl -k -I https://127.0.0.1:19443
curl -k https://127.0.0.1:19443/api/health
```

ASR：

```bash
curl -fsS http://127.0.0.1:8020/health
python -m unittest services.asr_service.test_server
```

妆容评测 smoke：

```bash
python eval/makeup/scripts/run_eval_pipeline.py \
  --project-root . \
  --backend-url http://127.0.0.1:13000 \
  --limit 2 \
  --vlm-mode mock
```
