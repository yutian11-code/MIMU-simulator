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

评测工具：

```bash
cd /storage/nvme3/shushanfu/MIMU-colleague
/home/shushanfu/software/Anaconda/envs/mimu-comfy/bin/python -m unittest discover -s eval/makeup/tests -v
/home/shushanfu/software/Anaconda/envs/mimu-comfy/bin/python eval/makeup/run_eval_pipeline.py --manifest eval/makeup/manifests/regression_30.jsonl --output-dir eval/makeup/runs/regression_30 --backend-url http://127.0.0.1:13000
```

## 人工验收路径

1. 打开 `http://10.246.1.70:19006`。
2. 使用测试账号登录：`demo@beautyasset.app` / `demo123456`。
3. 进入推荐页，选择一个彩妆模板。
4. 查看模板图片和视频是否正常显示。
5. 进入方案结果页，使用“妆容预览”上传或拍摄一张正脸图。
6. 等待生成结果，确认页面能显示 `/makeup/result` 返回的图片。
7. 如浏览器无法访问摄像头，优先改用相册上传；再检查浏览器站点权限、HTTPS/HTTP 策略和设备摄像头占用。

## 还未完成的产品化工作

- 前端真实点击流需要在桌面 Web、手机浏览器、Expo Go 或原生包中各跑一次。
- 妆容迁移目前是同步请求，后续需要任务队列、进度查询、并发限制和超时清理。
- 当前评测集是 starter regression set，只能防回归，不能代表真实产品质量。
- 需要扩展 80-120 个授权或 AI 生成的多样化评测 case，并建立人工抽检机制。
- 用户人脸图片的存储周期、自动清理和隐私说明需要产品化前明确。
- Stable Makeup 本地补丁需要转成可复现的 fork、patch 或安装脚本。
