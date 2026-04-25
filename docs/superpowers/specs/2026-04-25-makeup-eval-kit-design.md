# MIMU 妆容效果评测集设计

日期：2026-04-25

## 背景

当前同事 demo 已经接入后端、前端和 ComfyUI Stable Makeup。后端 `/makeup` 可以调用 ComfyUI 并返回妆容迁移结果图。下一阶段的核心风险不再是服务能否跑通，而是生成效果是否稳定、是否保留身份、是否真的迁移妆容，以及失败样本能否被快速发现。

本设计定义一套低人工成本的 `MIMU Eval Kit`。它用 AI 和传统视觉指标先做全量初筛，再让人工只复核高风险、高分歧和代表性样本。

## 目标

1. 构建一个可复现的小规模妆容评测集，第一版覆盖 30 个固定回归 case，扩展版覆盖 80-120 个 case。
2. 批量调用现有后端 `/makeup` 接口，记录输出图、耗时、失败原因和 ComfyUI 元数据。
3. 自动生成多维评分，包括身份保留、妆容迁移、自然度、瑕疵和综合可用性。
4. 用多模态 AI 对三图组进行 JSON 打分，并和传统视觉指标互相校验。
5. 生成可浏览 HTML 报告，让团队快速看到最好、最差、分歧最大和相对上轮变化最大的样本。
6. 将人工复核量控制在每轮 20-30 个 case，而不是全量人工打分。

## 非目标

1. 第一版不做模型微调。
2. 第一版不建设复杂标注平台。
3. 第一版不依赖真实用户隐私照片作为默认数据源。
4. 第一版不把多模态 AI 评分视为最终真值，只作为初筛和排序信号。

## 数据集组成

每个评测 case 是一个三元组：

```json
{
  "id": "case_0001",
  "user_image": "assets/users/u001.jpg",
  "template_image": "assets/templates/t_blue_eye.jpg",
  "output_image": "runs/20260425_001/outputs/case_0001.png",
  "style": "blue_eye_makeup",
  "attributes": {
    "skin_tone": "light",
    "face_angle": "front",
    "lighting": "studio",
    "difficulty": "easy"
  }
}
```

第一版建议：

1. 用户脸：20 张，优先用 AI 生成或团队明确授权的正脸/半侧脸图片。
2. 妆容模板：10-15 张，覆盖裸妆、红唇、眼线、烟熏、亮片、腮红、欧美浓妆、自然通勤等风格。
3. 固定回归集：30 个 case，每次模型、依赖、workflow 或参数变化后都跑。
4. 扩展评测集：80-120 个 case，用于版本里程碑或模型方案对比。

## 数据来源策略

默认优先级：

1. AI 生成素材：用于早期评测，隐私风险最低，适合检测崩图、妆容迁移和自然度。
2. 团队授权素材：用于验证真实照片表现，必须记录授权和使用范围。
3. 用户上传素材：不进入评测集，除非后续单独设计用户授权机制。
4. 公开数据集：只有确认授权、许可证和再分发限制后才纳入。

AI 生成素材需要保存生成提示词、种子、模型来源和使用许可证说明，保证样本可复现。

## 目录结构

建议在顶层新增：

```text
eval/
  makeup/
    assets/
      users/
      templates/
    manifests/
      regression_30.jsonl
      extended_120.jsonl
    runs/
      20260425_001/
        outputs/
        metadata.jsonl
        auto_scores.jsonl
        vlm_scores.jsonl
        report.html
    prompts/
      vlm_judge_v1.md
    scripts/
      run_makeup_eval.py
      score_auto.py
      judge_with_vlm.py
      build_report.py
```

## 生成流程

`run_makeup_eval.py` 读取 manifest，逐条向后端发送：

```text
POST /makeup
multipart:
  userImage
  templateImage
```

每条 case 记录：

1. 请求开始时间和结束时间。
2. HTTP 状态码。
3. 后端返回的 `promptId`、`imageUrl`、`output.filename`、`output.subfolder`、`output.type`。
4. 输出图本地副本。
5. 错误堆栈摘要。
6. 生成耗时。

失败 case 不重试超过 1 次。重试仍失败时，标记为 `generation_failed` 并进入报告。

## 自动视觉评分

传统视觉指标负责便宜、稳定、可复现的信号：

1. `face_detect_success`：输入、模板、输出是否检测到人脸。
2. `face_count`：输出是否仍是单人脸。
3. `identity_similarity`：输入脸和输出脸的人脸 embedding 相似度，优先用 InsightFace/ArcFace。
4. `landmark_stability`：输出五官关键点是否相对输入明显漂移。
5. `makeup_region_delta`：眼部、唇部、脸颊区域颜色和纹理是否向模板靠近。
6. `background_drift`：非脸部区域是否被异常修改。
7. `image_quality`：模糊、过曝、欠曝、压缩伪影、尺寸异常。

这些指标不直接替代人工判断，但用于筛出明显失败、疑似身份改变和妆容未迁移样本。

## 多模态 AI 评分

`judge_with_vlm.py` 将输入脸、妆容模板、输出图三张图片发送给多模态模型，要求只返回 JSON：

```json
{
  "identity_score": 1,
  "makeup_transfer_score": 1,
  "naturalness_score": 1,
  "artifact_score": 1,
  "overall_score": 1,
  "failure_type": "none",
  "reason": "short reason in Chinese"
}
```

评分口径：

1. `identity_score`：1 表示不像本人，5 表示高度保留身份。
2. `makeup_transfer_score`：1 表示几乎没迁移，5 表示目标妆容特征明显迁移。
3. `naturalness_score`：1 表示非常假，5 表示自然贴脸。
4. `artifact_score`：1 表示无明显瑕疵，5 表示严重崩图或脏图。
5. `overall_score`：1 表示不可展示，5 表示可以作为产品结果展示。
6. `failure_type`：只能是 `none`、`identity_changed`、`makeup_missing`、`face_distorted`、`dirty_artifact`、`wrong_region`、`unsafe_or_invalid`。

隐私默认策略：如果 case 使用真实授权照片，第一版默认只允许本地多模态模型评分；如需外部 API，必须单独显式确认。

## 人工复核策略

人工不全量标注，只复核系统挑出的样本：

1. AI/自动指标认为最差的 10 个。
2. AI/自动指标认为最好的 5 个。
3. AI 评分和传统视觉指标分歧最大的 10 个。
4. 新版本相对上个版本变化最大的 5 个。

每轮人工复核目标是 20-30 个 case。人工只需给五个 1-5 分和一个失败类型，不写长评语。

人工复核结果用于校准：

1. 调整 VLM prompt。
2. 调整自动指标阈值。
3. 更新固定回归集中的代表性样本。
4. 标记 golden cases，作为后续模型对比的基准。

## 聚合与通过标准

第一版通过标准：

1. 生成成功率 >= 90%。
2. 严重崩图率 <= 10%。
3. 身份保留平均分 >= 3.5/5。
4. 妆容迁移平均分 >= 3.5/5。
5. 人工抽检可接受比例 >= 70%。
6. 单张生成耗时中位数 <= 60 秒。

硬性拦截：

1. 输出无人脸或多脸。
2. 身份相似度低于阈值且 VLM 也判定身份改变。
3. `artifact_score >= 4`。
4. 输出图无法访问或尺寸异常。

综合分只用于排序，不用于掩盖硬性失败。

## 报告设计

`report.html` 至少包含：

1. 总览指标：成功率、平均耗时、各维度均分、硬失败数量。
2. 三图对比：输入脸、妆容模板、输出图。
3. 排序视图：综合最好、综合最差、身份下降最多、妆容迁移最弱、瑕疵最高。
4. 版本对比：同一 case 在不同 run 之间的输出对比。
5. 可导出 CSV/JSONL，方便团队记录结论。

报告默认只生成本地静态文件，不上传任何图片。

## 接口与服务依赖

第一版依赖：

1. 后端服务：`http://127.0.0.1:13000`
2. ComfyUI 服务：由后端内部调用 `http://127.0.0.1:8188`
3. Python 环境：优先复用 `mimu-comfy`，因为其中已经安装 torch、insightface、Pillow 等视觉依赖。
4. 多模态评分：通过 provider adapter 接入，第一版允许先使用 mock judge 或人工导入结果，避免阻塞主流程。

## 风险与缓解

1. AI 评分不稳定：固定 prompt、固定输出 schema、保存模型名和版本，每次评分可复跑。
2. 合成脸与真实照片差异：第一版用合成脸降隐私风险，第二版加入少量授权真实照片校准。
3. 自动指标误判：传统指标只做筛选信号，最终结论以人工抽检校准。
4. 外部 VLM 隐私风险：默认本地评分；外部 API 必须单独开关。
5. 生成耗时长：评测脚本串行跑固定集，后续再加并发和队列。

## 验收清单

1. 能用 30 个固定 case 批量调用 `/makeup`。
2. 每个成功 case 都保存输入、模板、输出、耗时和后端响应元数据。
3. 自动评分文件 `auto_scores.jsonl` 可生成。
4. VLM 评分文件 `vlm_scores.jsonl` 可生成，或在未配置 VLM 时明确标记为 skipped。
5. `report.html` 可本地打开，并能按失败类型和分数排序。
6. 至少一轮人工复核结果可以回写到 `human_scores.jsonl`。
7. 后续模型或参数变化后，可以复用同一 manifest 做版本对比。

## 推荐实施顺序

1. 先做 manifest、批量调用和结果落盘。
2. 再做 HTML 三图报告。
3. 再加传统视觉自动评分。
4. 再加 VLM judge adapter。
5. 最后加人工复核回写和跨版本对比。
