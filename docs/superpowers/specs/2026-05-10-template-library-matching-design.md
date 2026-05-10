# MMU 模板库与智能匹配算法设计

## 背景

产品侧新增 `MMU模板库标准构建(1).docx`，定义了妆造风格、产品类目、标准化步骤、脸部操作区域、脸型和难度加权。昨天的 `妆容生成搭建模板.docx` 则强调不要做纯固定模板库，而是根据用户需求、画像和已有产品动态生成可执行模板。

本设计把两者合并：`MMU模板库标准构建` 作为标准知识库和检索语料，昨天的生成模板 PRD 作为个性化生成、产品槽位、快照和埋点体系。最终目标不是简单规则匹配，而是“多模态智能召回 + 模型重排 + 可解释规则约束 + 动态 3-5 步执行模板”。

## 目标

1. 按产品部门标准搭建模板库基础架构，保留标准风格、步骤、产品、脸型、区域和难度信息。
2. 设计一个体现算法能力的模板匹配流程，支持文本需求、用户画像、已有产品和可选参考图片。
3. 生成结果仍兼容当前 `makeup-templates` 动态模板域：模板、步骤、产品槽位、覆盖率、缺失项和事件埋点。
4. 在线链路不能独占全部 GPU。普通模板匹配应优先走离线向量索引、缓存、CPU 检索和轻量服务。
5. 给出可测试、可调参、可解释的评分公式和验收指标。

## 非目标

第一版不做完整商城推荐、不做自动视频拆解、不做实时每帧 VLM 匹配、不训练新模型、不把模板匹配服务设计成独占 8 卡的常驻重模型系统。参考图解析和 embedding 批处理可以用 GPU，但必须走共享调度和并发限制。

## 标准知识库

标准知识库不是最终给用户看的模板结果，而是算法可检索、可组合、可解释的底层语料。

### 风格体系

从新文档保留两层结构：

- 原子风格：伪素颜妆、通勤淡妆、清透裸妆、白开水妆、日杂妆、纯欲妆、韩系水光妆、甜妹妆、轻熟气质妆、法式慵懒妆、烟熏妆、欧美截断、新中式妆、复古港风妆、泰式妆、女团妆、Y2K 辣妹妆等。
- 风格族：日常通勤、韩系/日系少女、轻熟千金、亚裔混血、国风、欧美、舞台创意、特定视觉。

每个风格应转成结构化字段：`styleId`、`styleFamily`、`aliases`、`positiveTags`、`negativeTags`、`baseFinish`、`colorPalette`、`intensityLevel`、`defaultDifficulty`、`typicalScenes`。

### 产品与槽位体系

产品类目按文档标准化为妆前、底妆、定妆、眉妆、眼妆、修容、唇妆、卸妆、工具九类。每个类目继续保留细分属性：

- 质地：水润、哑光、丝绒、膏状、液体、粉状、喷雾等。
- 功能：控油、保湿、提亮、遮瑕、持妆、修饰脸型、提升气色等。
- 色号/色系：冷调、暖调、自然色、小麦色、豆沙色、奶茶色、番茄色、粉色系、橘色系等。
- 适用条件：肤质、妆效、场景、难度、可替代关系。

这些字段用于增强当前 `TemplateProductSlot` 的 `desiredEffect`、`desiredColorFamily`、`desiredFinish` 和 `fallbackInstruction`。

### 步骤体系

标准步骤保留 14 步：妆前护肤、防晒/隔离、遮瑕、底妆、定妆、眼影、眉毛、修容、高光、腮红、睫毛、眼线、唇妆、二次定妆。

用户端执行模板第一版仍输出 3-5 步。压缩规则为：

- 3 步：底妆准备、眉眼重点、气色与唇妆。
- 4 步：妆前底妆、眉眼、修容腮红、唇妆定妆。
- 5 步：妆前/底妆、眉毛、眼妆、腮红/修容、唇妆/定妆。

每个标准步骤应绑定 `operationAreas`，例如全脸、T 区、U 区、眼周、眉部、颧骨、下颌线、鼻周、唇部。这些字段后续可直接服务 AI 跟妆检测。

### 难度体系

沿用新文档难度公式：

`总难度分 = 步骤难度分 + 产品数量 + 特殊手法加分`

动作基础分作为规则层约束：

- 洁面、爽肤水、精华、乳液、面霜、防晒：1.0
- 隔离、粉底、散粉、定妆喷雾：1.2
- 基础遮瑕：1.3
- 腮红、高光、润唇膏、口红：1.5
- 眉毛、卧蚕、基础眼影：1.8
- 眼线、睫毛膏、修容、唇线：2.2
- 假睫毛、下睫毛、精准遮瑕：2.5
- 特殊手法出现时加 3 分

难度不是只用于展示，也参与重排。新手、快速妆、通勤妆对高难动作做惩罚；舞台、欧美、特定视觉妆允许更高难度。

## 模型与部署资源

当前模型统一在 `/storage/nvme3/shushanfu/checkpoint`。本设计优先复用已有模型：

- 文本 embedding：`Qwen3-Embedding-4B` 或 `Qwen3-Embedding-8B`
- 重排：`Qwen3-Reranker-8B`
- 文本意图解析：`Qwen3-1.7B`、`Qwen3-8B` 或现有 OpenAI-compatible LLM 服务
- 图片/参考妆容解析：`huggingface/Qwen/Qwen2.5-VL-32B-Instruct-AWQ`
- 高质量离线解析备选：`huggingface/Qwen/Qwen2.5-VL-72B-Instruct-AWQ`

如需补模型，使用：

```bash
HF_ENDPOINT=https://hf-mirror.com python /storage/nvme3/shushanfu/checkpoint/down_load.py ...
```

镜像失败时再加：

```bash
HTTP_PROXY=http://127.0.0.1:7890 HTTPS_PROXY=http://127.0.0.1:7890
```

### GPU 资源原则

8 卡要支撑整个业务，本板块不允许默认独占。当前硬件按用户说明为 GPU 0-3 四张 3090，GPU 4-7 四张 48G 4090。模板匹配只允许按需使用共享模型服务，不把 8 卡当作本模块专属资源。

建议约束：

1. 在线文本匹配默认不启动 VLM，不常驻独占新 GPU。
2. 模板 embedding 索引离线构建，低优先级批处理，可用单卡完成。
3. 参考图解析只在用户上传参考图时触发，走共享 VLM 服务，不新开独立 VLM 常驻实例。
4. 重排服务设置并发上限、超时和降级。超时后退回 embedding 分数加规则分。
5. `CUDA_VISIBLE_DEVICES` 必须可配置，禁止在代码中写死 0-7。
6. 推荐部署预算：embedding/reranker 最多占 1 张 3090 或 CPU fallback；VLM 复用现有 32B 服务，优先放在 4090 共享池；72B 仅离线批量标注使用，不进入默认在线链路。
7. 所有模型服务暴露健康检查和队列长度，业务请求根据负载自动降级。
8. 当妆容预览、实时跟妆、ASR 或其他业务占用 GPU 时，模板匹配必须自动降级为“已构建索引 + 规则重排”，保证推荐主流程可返回。

## 智能匹配流程

### 1. 输入归一化

输入来自用户自然语言、推荐场景、用户画像、已有产品、历史偏好和可选参考图片。

归一化输出 `TemplateMatchProfile`：

```json
{
  "scene": "COMMUTE",
  "styleTags": ["CLEAR", "DAILY_LIGHT"],
  "effectTags": ["DEWY", "GOOD_COMPLEXION"],
  "constraints": ["OWNED_PRODUCTS_FIRST", "FAST", "LOW_INTENSITY"],
  "skinType": "combination",
  "faceShape": "round",
  "skillLevel": "beginner",
  "preferredProductCategories": ["foundation", "lip", "blush"],
  "referenceImageFeatures": {
    "baseFinish": "dewy",
    "eyeIntensity": 0.3,
    "blushPlacement": "upper_cheek",
    "lipColorFamily": "milk_tea"
  }
}
```

文本需求先用规则词表做稳定解析，再用 LLM 做补充。参考图存在时由 VLM 输出结构化妆容特征，禁止把真实人脸图片发到外部服务。

### 2. 候选召回

候选召回使用多路召回，取并集后去重：

- 语义召回：用户需求 embedding 与模板描述 embedding 相似度 TopK。
- 风格召回：按 `styleFamily`、`aliases`、`positiveTags` 命中。
- 场景召回：通勤、约会、上镜、舞台等场景强过滤或加权。
- 参考图召回：参考图特征 embedding 与模板视觉描述 embedding 相似度 TopK。
- 历史召回：用户曾完成、收藏、反馈好的风格优先。

第一版建议 TopK：语义 20、风格 10、场景 10、参考图 10，合并后进入重排的候选控制在 30 个以内。

### 3. 模型重排

重排分两层：

1. `Qwen3-Reranker-8B` 对用户需求和候选模板描述做 pairwise relevance score。
2. 规则层注入业务约束，避免模型只按语义相似但忽略可执行性。

重排输入不包含原始人脸图片，只包含结构化特征、用户需求文本和模板文本。

### 4. 综合评分

最终分数建议为：

```text
score =
  0.25 * embedding_similarity
+ 0.20 * reranker_relevance
+ 0.15 * style_match
+ 0.10 * scene_match
+ 0.15 * product_coverage
+ 0.05 * user_profile_fit
+ 0.05 * history_preference
- 0.03 * difficulty_penalty
- 0.02 * missing_required_slot_penalty
```

权重第一版写成配置，不写死在业务逻辑中。解释字段必须返回每项分数，便于产品和测试判断为什么选中。

### 5. 模板适配

最高分候选不是直接返回，而是被改造成个性化执行模板：

1. 根据用户时间和熟练度决定输出 3、4 或 5 步。
2. 从 14 步标准流程合并步骤，保留风格关键动作。
3. 根据脸型和肤质调整说明，例如圆脸腮红位置偏上、油皮定妆加强 T 区。
4. 根据产品覆盖率决定是否替换槽位、合并槽位或给出缺失说明。
5. 生成每步 `aiDetectionArea`、`completionCriteria`、`failureFeedback` 和 `nextStepCondition`。

### 6. 产品槽位匹配

产品槽位匹配沿用当前 `MakeupTemplateSlotMatchingService` 的稳定规则，但增强标签：

- 类目强匹配：粉底、气垫、遮瑕、口红、唇釉等标准类目。
- 属性匹配：质地、色系、妆效、功能。
- 用户偏好：常用、最近使用、反馈好、快过期但可用。
- 约束过滤：过期、空瓶、敏感避雷、halal 限制。
- 替代关系：唇釉可替代腮红点拍、哑光棕眼影可替代眉粉、遮瑕可替代轻底妆局部修饰。

输出状态保持 `matched`、`substitutable`、`missing`。覆盖率按 required slot 计算，recommended slot 不应过度拉低结果。

## 数据模型建议

当前已有 `GeneratedMakeupTemplate`、`GeneratedTemplateStep`、`TemplateProductSlot`、`MakeupGenerationRequest`、快照和事件表。新标准库可新增独立数据结构，避免污染用户生成结果：

- `StandardMakeupStyle`：标准风格和风格族。
- `StandardMakeupTemplate`：可检索模板骨架。
- `StandardTemplateStepBlock`：标准步骤块。
- `StandardProductSlotSpec`：标准产品槽位规格。
- `TemplateEmbeddingIndex`：模板向量索引元数据。
- `TemplateMatchTrace`：本次匹配的候选、分数、重排和降级记录。

用户生成结果继续落入现有 `GeneratedMakeupTemplate`，并记录 `sourceStandardTemplateId`、`matchScore`、`matchTraceId` 等关联字段。

## API 设计建议

第一版保持现有 `/recommendations/generate` 和 `/makeup-templates/generate` 对前端兼容，在后端内部替换匹配实现。可新增调试接口，仅内部使用：

- `POST /makeup-template-library/rebuild-index`：重建模板 embedding 索引。
- `POST /makeup-template-library/match-debug`：返回候选、分数、重排原因和降级状态。
- `GET /makeup-template-library/styles`：查看标准风格族和风格标签。

线上用户接口不暴露模型细节，只返回最终模板、步骤、产品槽位、覆盖率和解释。

## 降级与错误处理

1. Embedding 服务不可用：回退到词表召回和规则重排。
2. Reranker 不可用：使用 embedding similarity 加业务规则分。
3. VLM 不可用：参考图解析标记为 skipped，继续文本匹配。
4. GPU 繁忙：排队超过阈值后直接降级，不阻塞推荐主链路。
5. 模板库为空或索引损坏：回退到当前 5 步规则模板。
6. 用户产品数据缺失：生成模板仍可用，但覆盖率为 0，并明确缺失产品槽位。

## 测试与评测

### 单元测试

- 意图解析：不同中文输入能归一化到正确场景、风格和约束。
- 模板召回：典型输入能召回预期风格族。
- 重排规则：产品覆盖率、难度和缺失槽位能影响排序。
- 槽位匹配：同类、替代、缺失、过期过滤全部可测。
- 降级：embedding/reranker/VLM 超时时仍返回可用模板。

### 离线评测集

构造 50-100 条文本 case，覆盖：

- 日常通勤、韩日少女、轻熟千金、亚裔混血、国风、欧美、舞台创意、特定视觉。
- 新手/熟手、快妆/完整妆、油皮/干皮、不同脸型。
- 产品充足、产品部分缺失、产品完全缺失。
- 有参考图和无参考图。

每条 case 标注期望风格族、可接受候选、应避开的高难步骤、必须匹配或必须缺失的产品槽位。

### 验收指标

- Top1 风格族准确率 >= 75%。
- Top3 可接受模板召回率 >= 90%。
- 必需产品槽位匹配准确率 >= 85%。
- 无模型服务时，规则降级链路 100% 返回 3-5 步模板。
- 普通文本匹配 P95 延迟不超过 2 秒；带参考图解析可异步或显示排队状态。
- 模板匹配服务默认不新增独占 8 卡常驻进程。

## 实施顺序建议

1. 先把标准知识库建成可维护 JSON/数据库种子，覆盖风格、步骤、产品槽位和难度。
2. 做离线 embedding 索引构建脚本，优先使用已有 `Qwen3-Embedding-4B/8B`。
3. 加模板匹配服务：多路召回、reranker 可选、规则重排、trace 输出。
4. 接入现有 `MakeupTemplateGenerationService`，让最终生成结果仍走当前表结构。
5. 增加评测集和 smoke 测试，确认有无 GPU 都能跑通。
6. 最后接参考图 VLM 解析，并把它做成可选增强，不阻塞主链路。

## 关键设计结论

本方案不是方案一的简单规则模板库，而是以模板库为标准语料，以 embedding、reranker 和 VLM 为智能匹配能力，以规则层保证稳定性和可解释性。它能展示算法工作量，也能控制 GPU 消耗：重模型用于离线索引、可选重排和参考图解析；在线主链路必须有缓存和降级，不能因为模板匹配板块占满 8 卡而影响化妆预览、实时跟妆、ASR 和其他服务。
