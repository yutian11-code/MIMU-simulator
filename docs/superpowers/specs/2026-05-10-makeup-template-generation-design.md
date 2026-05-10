# AI 妆容模板生成基本架构设计

## 背景

产品文档要求从“内置妆容模板库”转为“基于用户需求和用户已有产品的个性化模板生成系统”。系统需要根据用户自然语言、用户画像、已有产品、历史偏好和可选参考内容，生成可展示、可执行、可检测、可复用的个人妆容模板。

当前项目已经有 `POST /recommendations/generate`、`Recommendation`、`RecommendationStep`、静态前端模板和基础产品匹配服务。新设计不替换现有推荐链路，而是在后端新增独立模板生成域，并把生成结果映射回现有推荐结构，保证前端现有“生成今日妆容 -> 产品确认 -> 妆容预览 -> 执行 -> 跟妆”链路继续可用。

## 目标

1. 用户输入一句需求后，可以生成 3-5 步个人妆容模板。
2. 模板必须基于用户需求、用户条件快照和用户产品快照生成，而不是固定取库。
3. 每次生成都能追溯原始需求、解析结果、用户条件快照和产品快照。
4. 每个步骤必须绑定产品槽位，槽位能标记已匹配、可替代或缺失。
5. 系统能计算已有产品覆盖率、缺失产品类型和个性化生成理由。
6. 用户编辑、替换产品、跳过步骤、完成步骤和反馈都能结构化记录。
7. 前端可以直接根据模板结构展示执行流程，并继续兼容现有推荐结果结构。

## 非目标

第一版不做复杂视频解析、博主妆容自动拆解、精细脸型算法、具体商品购买推荐、高级审美评分、多模型自动评测和大规模模板推荐系统。这些能力依赖第一版沉淀的模板、槽位、执行和反馈数据。

## 方案选择

采用“独立生成模板表 + 兼容现有推荐接口”的方案。

后端新增 `makeup-templates` 领域模块，持久化产品文档要求的核心对象。现有 `/recommendations/generate` 内部优先调用新模板生成服务，再同步创建兼容的 `Recommendation` 和 `RecommendationStep`，返回当前前端已支持的 `RecommendationResult` 结构。这样既满足长期数据建模，又避免第一版大范围改前端。

不采用把所有字段塞进现有 `Recommendation` 表的方案，因为后期很难查询某个产品槽位、某类步骤失败率、某种风格生成准确度。也不采用步骤和槽位全部 JSON 化的折中方案，因为第一版就需要测试和统计产品匹配质量。

## ID 规则

技术侧第一版统一采用前缀加日期加随机短码：

- `greq_<yyyyMMdd>_<8hex>`：生成请求
- `ucsnap_<yyyyMMdd>_<8hex>`：用户条件快照
- `upsnap_<yyyyMMdd>_<8hex>`：用户产品快照
- `tmpl_<yyyyMMdd>_<8hex>`：生成妆容模板
- `tstep_<yyyyMMdd>_<8hex>`：模板步骤
- `slot_<yyyyMMdd>_<8hex>`：产品槽位
- `tevt_<yyyyMMdd>_<8hex>`：模板事件

这些 ID 是稳定业务 ID，不暴露数据库自增序列。后续如果团队有统一 ID 服务，只替换 ID 工厂，不改变业务模型。

## 数据模型

### MakeupGenerationRequest

记录用户本次为什么生成模板：

- `id`
- `userId`
- `rawUserInput`
- `parsedScene`
- `parsedStyleTags`
- `parsedEffectTags`
- `parsedConstraints`
- `referenceType`
- `referenceId`
- `generationSource`
- `createdAt`

### UserConditionSnapshot

记录生成时的用户条件，不依赖之后实时用户资料变化：

- `id`
- `userId`
- `skinTone`
- `skinType`
- `faceShape`
- `eyeShape`
- `makeupSkillLevel`
- `preferredStyles`
- `avoidStyles`
- `preferredFinish`
- `allergyOrAvoidNotes`
- `createdAt`

第一版从现有 `User.skinType`、`User.makeupPreference`、`User.commonScenarios` 推导；缺失字段用结构化空值或默认等级 `normal`。

### UserProductSnapshot

记录生成时的可用产品状态：

- `id`
- `userId`
- `availableProductCount`
- `availableCategories`
- `missingCategories`
- `ownedProducts`
- `expiredOrUnavailableProducts`
- `createdAt`

`ownedProducts` 是 JSON 数组，至少包含 `userProductId`、`productId`、`productCategory`、`subCategory`、`brandName`、`productName`、`colorFamily`、`finishType`、`suitabilityTags`、`status`、`usagePreference`。

### GeneratedMakeupTemplate

记录最终生成的模板主信息：

- `id`
- `userId`
- `requestId`
- `conditionSnapshotId`
- `productSnapshotId`
- `displayName`
- `templateType`
- `primaryScene`
- `stylePrimary`
- `styleTags`
- `effectTags`
- `overallEffect`
- `difficultyLevel`
- `estimatedTimeMinutes`
- `productCoverageRate`
- `ownedProductUsageCount`
- `missingProductTypes`
- `substitutionCount`
- `personalizationReasons`
- `generationConfidence`
- `templateReuseKey`
- `createdAt`
- `updatedAt`

### GeneratedTemplateStep

记录每个可执行步骤：

- `id`
- `templateId`
- `stepOrder`
- `sectionCode`
- `stepName`
- `stepGoal`
- `userInstruction`
- `visualChange`
- `aiDetectionArea`
- `completionCriteria`
- `failureFeedback`
- `editableByUser`
- `nextStepCondition`
- `createdAt`

步骤数量第一版控制在 3-5 步。默认五步骨架为 `BASE`、`BROW`、`EYE`、`BLUSH`、`LIP`，生成器可根据用户需求删减或合并。

### TemplateProductSlot

记录步骤绑定的产品槽位：

- `id`
- `templateId`
- `stepId`
- `slotCode`
- `category`
- `requiredLevel`
- `desiredEffect`
- `desiredColorFamily`
- `desiredFinish`
- `matchedUserProductId`
- `matchedProductId`
- `matchStatus`
- `matchReason`
- `alternativeProductIds`
- `fallbackInstruction`
- `createdAt`

`matchStatus` 第一版取值为 `matched`、`substitutable`、`missing`。已过期或空瓶产品不能成为 `matched`，只进入快照和原因说明。

### TemplateEvent

记录生成、编辑、执行和反馈埋点：

- `id`
- `userId`
- `sessionId`
- `requestId`
- `templateId`
- `stepId`
- `slotId`
- `productSnapshotId`
- `conditionSnapshotId`
- `eventName`
- `payload`
- `appVersion`
- `createdAt`

事件只保存结构化 ID、标签和分数，不保存原始人脸图片、视频和音频内容。

## 生成流程

1. `POST /makeup-templates/generate` 接收 `userId`、`rawUserInput`、`generationSource`、可选参考信息和约束。
2. 创建 `MakeupGenerationRequest`，并解析场景、风格、妆效和限制。
3. 读取当前用户资料，创建 `UserConditionSnapshot`。
4. 读取用户 `active`、`idle` 产品和不可用产品，创建 `UserProductSnapshot`。
5. 根据解析结果生成 3-5 步模板骨架和每步产品槽位。
6. 对每个产品槽位执行匹配算法，填充匹配产品、替代品、缺失状态和匹配原因。
7. 计算覆盖率、缺失品类、替代数量、置信度和个性化理由。
8. 保存 `GeneratedMakeupTemplate`、步骤和槽位。
9. 写入生成相关 `TemplateEvent`。
10. 调用兼容映射器，同步创建 `Recommendation` 和 `RecommendationStep`。
11. 返回完整模板响应；现有 `/recommendations/generate` 返回兼容的推荐响应。

## 意图解析

第一版使用规则解析和可选 LLM 增强：

- 场景关键词：通勤、约会、上镜、面试、日常、聚会。
- 风格标签：清透、自然、甜美、温柔、欧美、干净、显气色。
- 妆效标签：水光、哑光、奶油肌、持妆、遮瑕、提亮。
- 约束标签：快速、已有产品优先、敏感避雷、低饱和、不浓妆。

如果现有推荐 LLM 配置可用，LLM 可以生成标题、摘要、理由和步骤草案；规则层仍负责规范化字段、补齐槽位和保证测试稳定。LLM 不可用时，规则引擎必须能独立生成可用模板。

## 产品槽位匹配算法

第一版采用可测试的规则引擎：

1. 状态过滤：`expired`、`finished` 产品不能作为已匹配产品。
2. 类目强匹配：产品 `category/subCategory` 与槽位需求越接近分数越高。
3. 标签匹配：产品 `tags/userTags` 与 `desiredEffect`、`desiredFinish`、模板风格标签交集越多越优先。
4. 偏好加权：用户常用、喜欢、最近使用产品加分。
5. 临期加权：可用但临近过期产品适度加分，便于优先消耗。
6. 限制扣分：Halal、敏感肌、避雷说明等约束可扣分或禁止。
7. 替代判断：同大类但子类不完全一致时可标记 `substitutable`。
8. 缺失判断：没有可用候选时标记 `missing` 并生成 `fallbackInstruction`。

覆盖率计算为：`matched required slots / total required slots`。可选槽位不拉低覆盖率，但会计入替代和缺失说明。

## 接口设计

### POST /makeup-templates/generate

请求：

```json
{
  "userId": "user-001",
  "rawUserInput": "明天上班想画清透又显气色的妆，最好用我已有的产品",
  "generationSource": "recommendation_scenario",
  "referenceType": "none",
  "referenceId": null,
  "requirements": ["已有产品优先", "快速", "清透"]
}
```

响应返回完整模板、步骤、槽位、覆盖率、缺失品类和快照 ID。

### GET /makeup-templates/:templateId

返回完整模板详情，用于后续模板库、复用和调试。

### POST /makeup-templates/:templateId/events

记录用户行为事件。请求包含 `eventName`、可选 `stepId`、`slotId`、`payload` 和 `sessionId`。

### POST /recommendations/generate

保持现有请求兼容。内部调用新模板服务后，把结果映射成当前 `RecommendationResponseDto`：

- `id` 使用同步创建的 `Recommendation.id`
- `scenario` 使用模板 `primaryScene` 或原输入
- `title` 使用 `displayName`
- `summary` 包含覆盖率和缺失品类
- `steps` 使用模板步骤，并保留 `matchedProductId`、`alternativeProductIds`、`missing`
- `reasons` 使用 `personalizationReasons`

响应可以附加可选字段 `generatedTemplateId`、`productCoverageRate`、`missingProductTypes`、`productSlots`。前端旧代码忽略这些字段也能继续运行。

## 前端兼容

第一版前端只做必要类型扩展：

- `RecommendationResult` 可选增加 `generatedTemplateId`、`productCoverageRate`、`missingProductTypes`。
- `RecommendationResultStep` 可选增加 `sectionCode`、`stepGoal`、`visualChange`、`aiDetectionArea`、`completionCriteria`、`failureFeedback`、`productSlots`。
- 当前页面继续读取 `steps`、`matchedProductId`、`alternativeProductIds`、`missing`。
- 静态 mock 模板继续作为后端不可用 fallback。

后续 UI 可以基于新增字段展示覆盖率、缺失槽位、匹配原因和产品替换入口。

## 事件设计

第一版至少记录这些事件：

- `template_generation_started`
- `user_intent_parsed`
- `user_condition_snapshot_created`
- `user_product_snapshot_created`
- `product_slots_created`
- `owned_products_matched`
- `template_steps_created`
- `ai_detection_rules_created`
- `template_generation_completed`
- `product_replaced_by_user`
- `step_completed`
- `step_skipped`
- `manual_override_used`
- `template_feedback_submitted`
- `product_match_feedback_submitted`

现有执行接口更新进度和反馈时，应同步写入模板事件。若执行来自旧推荐且没有 `generatedTemplateId`，事件写入可以跳过，不影响旧链路。

## 错误处理

- 用户不存在：返回 404。
- 用户输入为空：返回 400。
- 用户没有任何可用产品：仍生成模板，所有必需槽位标记为 `missing`，覆盖率为 0。
- LLM 不可用或返回非法 JSON：记录警告，使用规则生成器兜底。
- 产品快照创建成功但后续生成失败：请求和快照保留，事件记录失败原因，接口返回 500。
- 同步创建兼容 `Recommendation` 失败：模板保留，接口返回包含模板 ID 的错误，便于排查和重试。

## 测试策略

后端单元测试：

1. 规则解析能从自然语言中提取场景、风格、妆效和约束。
2. 用户条件快照不会随之后用户资料变化而改变。
3. 产品快照区分可用产品和过期/空瓶产品。
4. 有底妆、眉笔、散粉时能命中对应槽位。
5. 缺腮红或唇妆时能标记 `missing`。
6. 过期产品不会成为 `matched`。
7. 覆盖率按必需槽位正确计算。
8. 每个步骤至少有一个产品槽位和 AI 检测字段。
9. 生成结果能映射为现有 `RecommendationResponseDto`。
10. 编辑、替换、完成、跳过和反馈事件能写入并关联模板、步骤和槽位。

后端集成测试：

- `POST /makeup-templates/generate` 生成完整模板。
- `GET /makeup-templates/:templateId` 能读取模板详情。
- `POST /makeup-templates/:templateId/events` 能记录事件。
- `POST /recommendations/generate` 仍返回前端兼容结构。

前端验证：

- TypeScript 类型检查通过。
- 现有生成今日妆容、产品确认、妆容预览、执行和跟妆页面能消费兼容响应。

## GPU 使用

第一版模板生成和匹配默认在后端 CPU 规则层完成，不占用 GPU。只有在已配置 LLM 或后续接入视觉参考解析时才可能调用模型。用户要求当前只使用 0-1 卡；本设计阶段不启动模型。实现和测试阶段默认不使用 3-7 卡，除非 3 小时后确认其他卡空闲且确有模型推理需求。

## 验收标准

1. 用户输入一句需求，可以生成一套个人妆容模板。
2. 模板根据用户需求和用户产品动态生成，不是固定取库。
3. 生成请求、用户条件快照和产品快照都能被查询或通过模板关联追溯。
4. 每个步骤都绑定产品槽位。
5. 每个槽位都有 `matched`、`substitutable` 或 `missing` 状态。
6. 模板能计算已有产品覆盖率。
7. 用户修改步骤、替换产品、跳过步骤、完成步骤和反馈都能记录为事件。
8. 反馈能关联到具体模板、步骤和产品槽位。
9. 后端测试覆盖核心匹配和兼容映射。
10. 前端现有推荐执行链路不因新结构中断。
