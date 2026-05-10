# 智能妆容模板匹配测试说明

> 目标读者：产品、前端、后端联调同学。
> 更新时间：2026-05-10。

## 1. 这次做了什么

这次新增的是“按产品部门模板标准搭建模板基本架构，并完成算法匹配”的后端能力。核心不是单纯关键词 if/else，而是一个可降级的混合匹配链路：

1. 解析用户意图：从自然语言里提取场景、风格、妆效和约束。
   - 场景：`COMMUTE`、`DATE`、`INTERVIEW`、`CAMERA` 等。
   - 风格：`CLEAR`、`NATURAL`、`SWEET`、`GENTLE`、`ELEGANT`、`Y2K`、`IDOL`、`VISUAL` 等。
   - 约束：`FAST`、`LOW_INTENSITY`、`OWNED_PRODUCTS_FIRST` 等。
   - 英文/全角关键词已归一化，例如 `Y2K`、`Y2k`、`Ｙ２Ｋ` 都能识别。

2. 标准模板库：内置 8 类标准妆容家族。
   - `DAILY_COMMUTE` 日常通勤
   - `KOREAN_JAPANESE_GIRL` 韩日甜妹
   - `ELEGANT_LUXURY` 轻熟千金
   - `ASIAN_MIXED` 亚裔混血
   - `CHINESE_STYLE` 国风
   - `WESTERN` 欧美
   - `STAGE_CREATIVE` 舞台创意
   - `SPECIFIC_VISUAL` 特定视觉，如 Y2K、女团、辣妹

3. 匹配算法：综合模板描述相似度、风格标签、场景、已有产品覆盖率、用户难度适配、缺失产品惩罚。配置 embedding/reranker 服务时会用模型分数；未配置时自动降级为本地可解释打分。

4. 生成个性化妆容模板：匹配到标准模板后，会按用户已有产品做产品槽位匹配，生成分步执行模板、缺失产品、替代品、完成条件和失败反馈。

5. 推荐链路已接入：`POST /recommendations/generate` 会走新模板生成链路，并在返回结果里带 `generatedTemplateId`、`productCoverageRate`、`missingProductTypes` 等字段。

## 2. 前端现在多了什么能力

前端现在有两条入口：

- 模板库管理：`个人档案 -> 模板库管理`，可导入标准模板、查看列表、编辑草稿、发布和回滚。
- 用户推荐链路：`生成今日妆容 -> 推荐结果 -> 产品清单 -> 执行步骤`，推荐算法读取数据库中已发布的模板版本。

模板库管理页现在会显示：

- 模板状态：草稿、已发布、已归档。
- 当前版本号、风格族、预计分钟数。
- seed 按钮：将产品文档中的 8 类标准模板写入数据库。
- 详情页：编辑模板名称、描述、场景、风格、模板说明、视觉说明和变更说明。
- 版本页：查看版本历史，并将历史版本复制成新的已发布版本完成回滚。

推荐结果页现在会显示：

- 命中模板族，例如 `轻熟千金`、`国风新中式`、`欧美系`。
- 标准模板 ID，例如 `std_elegant_luxury`。
- 产品覆盖率和匹配强度。
- 缺失产品类型。
- 个性化推荐理由。

产品清单页现在会显示：

- 5 个正式执行步骤，不再只显示有匹配产品的步骤。
- 每一步下的产品槽位，例如 `BASE_FOUNDATION`、`EYE_SHADOW_OR_LINER`、`LIP_COLOR`。
- 槽位状态：已匹配、可替代、待补齐。
- 匹配原因和没有产品时的 fallback 操作建议。

执行页现在会显示当前步骤的：

- 完成标准 `completionCriteria`。
- 易错提醒 `failureFeedback`。
- AI 检测区域 `aiDetectionArea`。
- 视觉变化 `visualChange`。

## 2.1 真实用户旅程：正式版前端验证路径

这一节按“我是一个真实用户”的方式测试。现在的验证重点已经从“接口旁证”变成“前端页面直接可见”：用户输入需求后，应能在推荐结果页看到命中模板证据，在产品清单页看到槽位匹配状态，在执行页看到本步完成标准。

### 管理旅程：初始化、编辑、发布、回滚模板

**用户角色**

我是模板运营或算法联调同学，需要确认产品文档中的标准模板已经进入数据库，并且前端能完成模板管理。

**前端操作**

1. 打开前端并登录 demo 账号。
2. 进入 `个人档案`。
3. 点击 `模板库管理`。
4. 如果列表为空，点击右上角云上传图标导入标准模板。
5. 列表应出现 8 个标准模板，包含通勤、韩日甜妹、轻熟千金、亚裔混血、国风、欧美、舞台创意、特定视觉。
6. 点击任意模板进入详情页。
7. 修改“变更说明”或模板描述，点击 `保存草稿`。
8. 详情页状态应变为 `draft`，当前版本号增加。
9. 点击 `发布当前草稿`。
10. 状态应变为 `published`，该版本成为当前版本。
11. 点击右上角时钟图标进入版本历史。
12. 对非当前发布版本点击 `回滚到此版本`。
13. 系统应生成一个新的已发布版本，历史版本不被覆盖。

**后端旁证**

```bash
curl -fsS \
  -H 'Authorization: Bearer demo-token' \
  http://127.0.0.1:13001/makeup-template-library/templates | python -m json.tool
```

预期：

- `items.length` 至少为 8。
- 每个已发布模板都有 `currentVersion`。
- `currentVersion.stepBlocks` 和 `currentVersion.productSlots` 非空。

### 用户旅程：生成一套面试轻熟知性妆

**用户动机**

我明天有面试，希望妆容看起来专业、知性、有气色，但不要太浓。我希望系统识别为轻熟/优雅方向，而不是普通通勤淡妆。

**前端操作**

1. 打开前端并登录 demo 账号。
2. 从首页点击“生成今日妆容”，进入定制页。
3. 在“场景”里可以选“通勤”；当前场景按钮不一定有“面试”，所以把关键需求写进“自由补充”。
4. 在“风格2”里选“自然”或更接近的风格。
5. “肤质状态”“妆感强度”“时间预估”“难度期望”按测试需要选择即可，建议先保持默认或选轻量妆感。
6. 在“自由补充”输入：

```text
面试需要轻熟知性优雅妆，不要太浓
```

7. 点击“开始生成”，等待 loading 页跳转到推荐结果页。

**推荐结果页应该看到什么**

- 页面进入“推荐方案”，不是空白页或失败页。
- “AI 推荐理由”展示时间、已拥有产品数量和可跟练步骤数。
- “Template Match”卡片展示：
  - 命中模板：应接近“轻熟千金”。
  - 标准模板 ID：应为 `std_elegant_luxury`。
  - 产品覆盖：例如 `40%`、`60%`，以当前用户资产为准。
  - 匹配强度：来自 `matchScore`。
  - 缺失产品：展示缺失槽位类型；如果关键槽位全覆盖，则显示已覆盖。
- “步骤概览”展示 5 步正式执行步骤：底妆、眉毛、眼妆、腮红/轮廓、唇妆/定妆。

**产品清单页应该看到什么**

1. 在推荐结果页点击“产品清单”卡片。
2. 页面标题为“本次需要使用的产品”。
3. 页面展示 5 个步骤，不应只展示已有产品的步骤。
4. 每个步骤的产品卡下方展示产品槽位，例如：
   - `BASE_PRIMER`
   - `BASE_FOUNDATION`
   - `BASE_CONCEALER`
   - `SETTING_PRODUCT`
   - `BROW_PENCIL`
   - `EYE_SHADOW_OR_LINER`
   - `CHEEK_BLUSH`
   - `CONTOUR_HIGHLIGHT`
   - `LIP_COLOR`
   - `MAKEUP_TOOL`
5. 每个槽位展示状态：
   - “已匹配”：用户已有产品可直接使用。
   - “可替代”：可用已有产品替代完成。
   - “待补齐”：当前资产缺产品，并显示 fallback 操作建议。
6. 底部点击“确认使用这些产品”返回推荐结果页。

**普通执行页应该看到什么**

1. 在推荐结果页点击“普通执行”。
2. 页面展示当前第几步、进度条和步骤 rail。
3. 当前步骤说明下方展示“本步判定标准”，包含：
   - 完成标准：例如底妆是否均匀、眉形是否平衡。
   - 易错提醒：例如底妆偏厚、眉头过重、眼影过深时如何修正。
   - AI 检测区域：例如 `full_face`、`brows`、`eyes`、`cheeks`、`lips`。
   - 视觉变化：用户完成这一步后应该看到的妆效变化。
4. 点击“下一步”应进入下一步骤；点击“跳过此步”应记录跳过并继续。

**AI 跟妆入口应该怎么测**

1. 在推荐结果页点击“AI 化妆师实时指导”。
2. Web 端会进入教练页，移动端会尝试进入实时摄像头跟妆页。
3. 这条路径用于验证实时教练入口和当前模板步骤是否能接上；模板匹配本身的可见验证以前三页为准。

### 换输入验证其他模板族

同一条前端路径可以替换“自由补充”来验证不同模板族：

| 测试目标 | 自由补充输入 | 推荐结果页应命中 |
| --- | --- | --- |
| 特定视觉 / Y2K | `今晚想试 Y2K 辣妹女团上镜妆` | 特定视觉，`std_specific_y2k_spicy` |
| 国风新中式 | `想要新中式复古港风红唇妆` | 国风新中式，`std_chinese_style` |
| 欧美系 | `拍照想要轻欧美截断眼妆和哑光底妆` | 欧美系，`std_western` |
| 舞台创意 | `万圣节想画朋克舞台妆，需要浓一点有冲击力` | 舞台创意，`std_stage_creative` |
| 韩系/日系少女 | `周末约会想画韩系水光甜妹初恋妆` | 韩系/日系少女，`std_korean_japanese_girl` |
| 亚裔混血 | `约会想要泰式混血感修容妆，轮廓清晰一点` | 亚裔混血，`std_asian_mixed` |

### 联调旁证：确认算法选型

前端已经直接展示模板命中结果。联调时如果需要排查“前端显示不对还是后端匹配不对”，再用 `match-debug` 做旁证：

```bash
curl -fsS \
  -H 'Authorization: Bearer demo-token' \
  -H 'Content-Type: application/json' \
  -d '{"rawUserInput":"面试需要轻熟知性优雅妆，不要太浓"}' \
  http://127.0.0.1:13001/makeup-template-library/match-debug | python -m json.tool
```

预期重点字段：

```json
{
  "selectedTemplateId": "std_elegant_luxury",
  "selectedTemplateVersionId": "std_elegant_luxury_v1",
  "selectedFamily": "ELEGANT_LUXURY"
}
```

全角/混合大小写输入也应正常归一化，例如：

```bash
curl -fsS \
  -H 'Authorization: Bearer demo-token' \
  -H 'Content-Type: application/json' \
  -d '{"rawUserInput":"今晚想试 Ｙ２k 女团上镜妆"}' \
  http://127.0.0.1:13001/makeup-template-library/match-debug | python -m json.tool
```

预期仍然选中 `std_specific_y2k_spicy` / `SPECIFIC_VISUAL`。

### 前端验收标准

- 用户能从“生成今日妆容”输入自然语言需求并生成推荐。
- 推荐结果页可见命中模板、标准模板 ID、覆盖率、匹配强度和缺失产品。
- 产品清单页可见 5 步，以及每步 `productSlots` 的已匹配/可替代/待补齐状态。
- 执行页可见完成标准、错误反馈、AI 检测区域和视觉变化。
- 面试轻熟妆命中 `ELEGANT_LUXURY`，不是通勤妆。
- Y2K/女团/辣妹输入命中 `SPECIFIC_VISUAL`，并能识别全角混合大小写 `Ｙ２k`。

## 3. 服务要求

后端需运行，例如当前常驻服务：

```bash
http://127.0.0.1:13001
```

局域网同学可用：

```bash
http://10.246.1.70:13001
```

认证 token：

```bash
demo-token
```

## 4. 快速确认后端可用

```bash
curl -fsS http://127.0.0.1:13001/health
```

预期：

```json
{"status":"ok","stage":"auth-bootstrap"}
```

## 5. 测试 1：查看标准模板库

```bash
curl -fsS \
  -H 'Authorization: Bearer demo-token' \
  http://127.0.0.1:13001/makeup-template-library/styles | python -m json.tool
```

预期能看到 `items` 数组，里面包含 8 类标准风格，例如：

- `DAILY_COMMUTE`
- `ELEGANT_LUXURY`
- `SPECIFIC_VISUAL`
- `WESTERN`

这个接口用于确认“模板库标准架构”已经存在。

## 6. 测试 2：直接测试匹配算法

### 6.1 通勤清透妆

```bash
curl -fsS \
  -H 'Authorization: Bearer demo-token' \
  -H 'Content-Type: application/json' \
  -d '{"rawUserInput":"明天上班想画清透白开水通勤妆，十分钟内完成"}' \
  http://127.0.0.1:13001/makeup-template-library/match-debug | python -m json.tool
```

预期重点字段：

```json
{
  "selectedTemplateId": "std_daily_clear_commute",
  "selectedFamily": "DAILY_COMMUTE"
}
```

### 6.2 轻熟知性面试妆

```bash
curl -fsS \
  -H 'Authorization: Bearer demo-token' \
  -H 'Content-Type: application/json' \
  -d '{"rawUserInput":"面试需要轻熟知性优雅妆，不要太浓"}' \
  http://127.0.0.1:13001/makeup-template-library/match-debug | python -m json.tool
```

预期重点字段：

```json
{
  "selectedTemplateId": "std_elegant_luxury",
  "selectedTemplateVersionId": "std_elegant_luxury_v1",
  "selectedFamily": "ELEGANT_LUXURY"
}
```

### 6.3 Y2K 女团辣妹上镜妆

```bash
curl -fsS \
  -H 'Authorization: Bearer demo-token' \
  -H 'Content-Type: application/json' \
  -d '{"rawUserInput":"今晚想试 Y2K 辣妹女团上镜妆"}' \
  http://127.0.0.1:13001/makeup-template-library/match-debug | python -m json.tool
```

预期重点字段：

```json
{
  "selectedTemplateId": "std_specific_y2k_spicy",
  "selectedFamily": "SPECIFIC_VISUAL"
}
```

### 6.4 全角/混合大小写 Y2K

```bash
curl -fsS \
  -H 'Authorization: Bearer demo-token' \
  -H 'Content-Type: application/json' \
  -d '{"rawUserInput":"今晚想试 Ｙ２k 女团上镜妆"}' \
  http://127.0.0.1:13001/makeup-template-library/match-debug | python -m json.tool
```

预期仍然选中：

```json
{
  "selectedTemplateId": "std_specific_y2k_spicy",
  "selectedFamily": "SPECIFIC_VISUAL"
}
```

## 7. 测试 3：跑完整评测集

仓库里已经加了 11 条 smoke 评测：

```bash
python eval/template_matching/run_template_matching_eval.py \
  --backend-url http://127.0.0.1:13001 \
  --token demo-token
```

预期：

```json
{
  "passed": 11,
  "total": 11,
  "failures": []
}
```

这 11 条覆盖：

- 清透通勤
- 韩系甜妹约会
- 轻熟知性面试
- 泰式/亚裔混血
- 新中式复古红唇
- 轻欧美拍照
- 欧美烟熏
- 朋克舞台/万圣节
- Y2K 女团辣妹
- 女团上镜

## 8. 测试 4：生成一个个性化妆容模板

```bash
curl -fsS \
  -H 'Authorization: Bearer demo-token' \
  -H 'Content-Type: application/json' \
  -d '{
    "rawUserInput":"面试需要轻熟知性优雅妆，不要太浓",
    "generationSource":"manual-test",
    "referenceType":"none",
    "requirements":["不要太浓"]
  }' \
  http://127.0.0.1:13001/makeup-templates/generate | python -m json.tool
```

预期重点看这些字段：

- `displayName`：应是轻熟/千金/优雅相关模板名。
- `sourceStandardTemplateId`：应为 `std_elegant_luxury`。
- `matchScore`：有算法匹配分。
- `matchTraceId`：有匹配轨迹 ID。
- `productCoverageRate`：已有产品覆盖率。
- `missingProductTypes`：缺失产品类型。
- `steps`：分步模板。
- `steps[].productSlots`：每一步需要什么产品、是否匹配到已有产品、替代品和 fallback 指引。
- `steps[].completionCriteria`：这一步怎么判断完成。
- `steps[].failureFeedback`：失败或画错时怎么提醒。

这个接口是最能直观看到“模板生成架构”成果的接口。

## 9. 测试 5：走前端已有推荐链路

如果你从前端页面点“生成推荐”，后端接口对应的是：

```bash
POST /recommendations/generate
```

也可以直接用 curl 模拟：

```bash
curl -fsS \
  -H 'Authorization: Bearer demo-token' \
  -H 'Content-Type: application/json' \
  -d '{
    "userId":"user-001",
    "scenario":"面试",
    "scenarioDetails":"面试需要轻熟知性优雅妆，不要太浓",
    "requirements":["不要太浓"]
  }' \
  http://127.0.0.1:13001/recommendations/generate | python -m json.tool
```

预期重点字段：

- `generatedTemplateId`：说明推荐结果来自新生成模板。
- `sourceStandardTemplateId`：命中的标准模板。
- `sourceStandardTemplateVersionId`：命中的标准模板版本。
- `templateFamily`：命中的模板族。
- `matchScore`：匹配分。
- `productCoverageRate`：产品覆盖率。
- `missingProductTypes`：缺失产品。
- `personalizationReasons`：个性化推荐理由。
- `steps[].title` / `steps[].instruction`：已经由生成模板转换成推荐步骤。
- `steps[].productSlots`：每步产品槽位。
- `steps[].completionCriteria` / `steps[].failureFeedback` / `steps[].aiDetectionArea`：执行页使用的判定标准。

## 10. 模型服务说明

当前算法支持可选模型增强：

- `TEMPLATE_EMBEDDING_BASE_URL`
- `TEMPLATE_EMBEDDING_MODEL`
- `TEMPLATE_RERANKER_BASE_URL`
- `TEMPLATE_RERANKER_MODEL`
- `TEMPLATE_MODEL_TIMEOUT_MS`

如果这些环境变量没配置，接口仍然可用，会返回：

```json
{
  "modelStatus": {
    "embedding": "unavailable",
    "reranker": "unavailable",
    "vlm": "skipped"
  },
  "degraded": true
}
```

这不是失败，而是本地降级打分生效。路演和 smoke 测试可以不依赖 GPU 模型。

## 11. 常见问题

### 11.1 前端入口在哪里？

现在有两个入口：

- 模板库平台入口：`个人档案 -> 模板库管理`。
- 用户推荐验证入口：`生成今日妆容`，生成后在推荐结果页、产品清单页和普通执行页查看新增字段。

### 11.2 如何证明不是旧逻辑？

用这两个 case：

- `面试需要轻熟知性优雅妆，不要太浓` 应选 `ELEGANT_LUXURY`，不是通勤妆。
- `今晚想试 Ｙ２k 女团上镜妆` 应选 `SPECIFIC_VISUAL`，并且能识别全角混合大小写 `Ｙ２k`。

这两个是这次修复前会出问题的典型 case。

### 11.3 为什么 score 不高？

当前未接 embedding/reranker 时是降级打分，分数用于排序，不是百分制质量分。只要 `selectedTemplateId` 和 `selectedFamily` 符合预期，就说明匹配链路正确。

### 11.4 可以让前端同学怎么测？

前端同学可以先直接调：

```bash
POST http://10.246.1.70:13001/recommendations/generate
```

看响应里是否出现：

- `generatedTemplateId`
- `sourceStandardTemplateId`
- `sourceStandardTemplateVersionId`
- `templateFamily`
- `matchScore`
- `productCoverageRate`
- `missingProductTypes`
- `steps[].productSlots`
- `steps[].completionCriteria`

然后打开前端同一条链路确认这些字段已经显示在结果页、产品页和执行页。
