# 模板库生产运营 Runbook

> 更新时间：2026-05-14
> 适用范围：模板库 P0 上线、运营批量处理、生成结果转正式模板、生产匹配验收

## 1. 目标

本次上线的目标不是再新增一套演示页，而是把当前模板库收敛成一个可运营、可回查、可控风险的正式工作面。

核心要求：

1. 生产匹配只能读取经过运营质量门禁的正式模板。
2. 机器导入与生成结果不会再自动混入生产匹配池。
3. 运营可以批量处理质量分层、归档和生成结果处置。
4. 整条链路可以通过前端与接口双重方式验证。

## 2. 生产门禁

只有同时满足以下条件的正式模板，才允许进入生产匹配池：

- `status = published`
- `visibility != private`
- `qualityReviewStatus = reviewed`
- `qualityTier in (P1, P2)`

以下内容仍然保留在库里，但默认不得进入生产匹配：

- `P3`
- `qualityReviewStatus != reviewed`
- `visibility = private`
- 已归档模板

## 3. 前置条件

开始前确认：

1. PostgreSQL 可连接，且 Prisma migration 已同步。
2. 后端可启动并能访问数据库。
3. 前端可打开 `模板库管理` 与 `运营工作台`。
4. demo 账号可正常登录，并能区分 `admin / operator / viewer`。
5. embedding、reranker 服务已健康，否则不要做模板匹配验收。

推荐健康检查：

```bash
curl -fsS http://127.0.0.1:13000/health
curl -fsS http://127.0.0.1:13001/platform/health
```

## 4. 启动顺序

### 4.1 后端

```bash
cd backend
npm run prisma:generate
npm run db:migrate
npm run start:dev
```

### 4.2 前端

```bash
cd frontend
npm run web
```

### 4.3 入口

- 前端 Web：`http://127.0.0.1:19006`
- HTTPS 路演入口：`https://10.246.1.70:19443`
- 后端：`http://127.0.0.1:13000`

## 5. Backfill 流程

P0 上线前，必须先把当前模板库做一次标准化处理。

本次在 2026-05-14 的实测结果：

- 标准正式模板共 `139`
- curated/MMU baseline 模板 `8`
- machine/public-video 模板 `131`
- 生成结果待处置 `107`

### 5.1 Dry-run

```bash
cd backend
npm run ops:backfill-template-library -- --dry-run
```

Dry-run 需要重点确认：

1. 标准 curated/seed 模板会被标成 `reviewed`。
2. 机器模板默认会落到 `P3`。
3. 低信号或明显不适合生产的机器模板会被隐藏或归档。
4. Dry-run 只打印摘要，不写库。

本次 dry-run 实测摘要：

- `reviewedCuratedCount = 8`
- `pendingMachineCount = 131`
- `hiddenMachineCount = 131`
- `archivedMachineCount = 0`

### 5.2 Apply

```bash
cd backend
npm run ops:backfill-template-library -- --apply
```

Apply 后重点确认：

1. 至少有一批 seed/curated 模板进入 `P1/P2 + reviewed`。
2. 机器模板不会继续裸奔在生产池里。
3. 待复核队列与待转正式队列数量合理下降或重分布。

本次 apply 后数据库汇总：

- `qualityReviewStatus = reviewed, qualityTier = P1, visibility = team` -> `1`
- `qualityReviewStatus = reviewed, qualityTier = P2, visibility = team` -> `7`
- `qualityReviewStatus = pending, qualityTier = P3, visibility = private` -> `131`
- `generated_makeup_templates.review_state = pending` -> `107`

## 6. 运营主链路

### 6.1 质量分层队列

入口：

```text
个人档案 -> 模板库管理 -> 模板质量队列
```

运营需要能完成：

1. 默认先处理待复核 backlog。
2. 批量把合格模板设为 `P1/P2 + reviewed`。
3. 批量把低质量模板归档。
4. 单条模板补充质量分、原因、运营备注。

### 6.2 生成结果队列

入口：

```text
个人档案 -> 模板库管理 -> 生成结果队列
```

生成结果需要具备明确处置状态：

- `pending`
- `deferred`
- `materialized`
- `published`
- `rejected`
- `archived`

运营需要能完成：

1. 对 `pending` 结果做初筛。
2. 把可继续整理的结果标成 `deferred` 或 `materialized`。
3. 把明显无价值结果标成 `rejected` 或 `archived`。
4. 对高质量结果直接生成正式草稿或发布到正式模板库。

### 6.3 正式模板库

入口：

```text
个人档案 -> 模板库管理 -> 正式模板库
```

运营需要能完成：

1. 查看模板详情与版本历史。
2. 编辑草稿。
3. 发布正式版本。
4. 归档无效模板。
5. 回滚历史版本。

## 7. 前端验收

### 7.1 admin / operator

必测路径：

1. 打开 `运营工作台`，确认概览卡片可加载。
2. 从 `质量分层` 进入 backlog 队列，完成至少一组批量操作。
3. 从 `生成结果队列` 完成一条 `pending -> materialized` 或 `pending -> published`。
4. 在 `正式模板库` 打开被转正的模板，完成保存草稿与发布。
5. 返回 `统一任务中心`，确认能看到对应运营记录。
6. 走一遍用户推荐链路，确认新生产模板能够被消费。

### 7.2 viewer

只读验收：

1. 可以查看工作台、质量队列、生成结果、正式模板、任务中心。
2. 不允许执行保存、批量操作、物化、发布、归档、回滚。

## 8. 接口验收

### 8.1 工作台

```bash
curl -fsS http://127.0.0.1:13000/ops-workbench/summary \
  -H "Authorization: Bearer $DEMO_TOKEN"

curl -fsS "http://127.0.0.1:13000/ops-workbench/tasks?limit=10" \
  -H "Authorization: Bearer $DEMO_TOKEN"

curl -fsS http://127.0.0.1:13000/ops-workbench/pending \
  -H "Authorization: Bearer $DEMO_TOKEN"
```

### 8.2 正式模板质量队列

```bash
curl -fsS "http://127.0.0.1:13000/makeup-template-library/quality-queue" \
  -H "Authorization: Bearer $DEMO_TOKEN"
```

### 8.3 生成结果队列

```bash
curl -fsS "http://127.0.0.1:13000/makeup-templates/generated?scope=all&limit=20" \
  -H "Authorization: Bearer $DEMO_TOKEN"
```

### 8.4 推荐链路

```bash
curl -fsS http://127.0.0.1:13000/recommendations/generate \
  -H "Authorization: Bearer $DEMO_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "scenario": "通勤",
    "scenarioDetails": "通勤淡妆，要求清透、自然、十分钟内完成",
    "requirements": []
  }'
```

验收重点：

1. 推荐成功返回。
2. 返回里能看到 `generatedTemplateId`。
3. 命中的标准模板应来自生产门禁后的候选池。

## 9. 任务回查

`统一任务中心` 或 `ops-workbench/tasks` 至少应能回查到这些事件：

- `quality_updated`
- `generated_materialized`
- `template_published`
- `template_rolled_back`
- `recommendation_consumed`
- 导入运行记录与失败重试记录

## 10. 回滚策略

如果上线后发现模板匹配池异常：

1. 暂停运营继续发布。
2. 检查 backfill 是否误标。
3. 检查是否有未复核模板被错误纳入生产池。
4. 必要时将异常模板批量归档或改回 `P3/pending`。
5. 使用模板版本回滚恢复最近稳定版本。

## 11. 上线通过标准

满足以下条件，才算 P0 可交付：

1. production gate 已生效。
2. backfill dry-run 与 apply 都跑通。
3. 运营能批量处理质量队列。
4. 运营能处置生成结果队列。
5. 新发布模板能进入推荐链路。
6. 工作台可回查运营动作与前台消费。
