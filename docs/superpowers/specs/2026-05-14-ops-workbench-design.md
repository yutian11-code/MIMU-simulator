# 运营工作台设计

> 目标：让运营和产品在明天的验收里，能稳定完成“生成结果入正式库、质量分层、正式模板发布、前台推荐命中、全链路回查”。

## 1. 背景与范围

当前项目已经具备以下基础能力：

- 正式模板库：草稿、发布、回滚、归档
- 质量分层：`P1 / P2 / P3` 和 `pending / reviewed / repaired / archived`
- 生成结果库：`GeneratedMakeupTemplate`
- 生成结果转正式模板：物化成草稿、继续编辑、发布
- 前台模板匹配：优先消费 `P1`，其次 `P2`

当前缺口不在“有没有能力”，而在“运营能不能稳定使用这些能力完成闭环”。主要问题是：

- 入口分散，运营无法在一个工作台里完成核心动作
- 角色和权限缺失，谁能发布、回滚、改质量结论没有边界
- 任务与操作记录分散，运营无法统一查看导入、物化、发布、回滚、命中
- 看板不存在，运营无法快速知道当前模板池和任务池状态
- 前台命中记录不可直接回查，无法证明“后台发布的模板已被前台实际消费”

本次设计范围限定为一个**运营可用版**子项目：

```text
生成结果 -> 质量分层 -> 正式模板发布 -> 前台推荐消费 -> 工作台回查
```

### 明天必须覆盖

1. 权限与角色：`admin / operator / viewer`
2. 运营统计看板
3. 统一任务中心
4. 质量分层稳定可用
5. 生成结果转正式模板稳定可用
6. 前台推荐能消费正式模板，并能被后台回查

### 明天明确不做

- 多级审核流
- 权限配置页面
- 复杂批量操作
- 离线统计仓库
- 统一异步任务引擎
- 重型图表大屏

## 2. 设计目标

### 2.1 业务目标

运营和产品可以在不查数据库的前提下完成以下动作：

1. 查看哪些模板需要处理
2. 查看哪些生成结果还未转正式模板
3. 将生成结果转成正式模板草稿
4. 编辑、发布、回滚正式模板
5. 维护模板质量分层
6. 查看前台是否已经命中并使用了这些模板
7. 回查最近导入、发布、回滚、命中记录

### 2.2 技术目标

1. 不推翻现有模板库、生成结果库、导入链路
2. 基于现有模块增量扩展
3. 统一运营读模型，而不是强行统一底层执行模型
4. 保证明天能交付，不引入重型新架构

## 3. 总体方案

采用一个**独立运营工作台**方案，保留现有模板详情编辑器和现有模板库服务层，新增：

1. 统一前端入口：`运营工作台`
2. 三角色权限模型：`admin / operator / viewer`
3. 统一任务中心读模型
4. 运营统计聚合服务
5. 审计与命中追踪

该方案不把所有动作都改造成统一任务执行器，而是按职责拆成两类：

- **真实运行任务**：如公有视频导入 run，继续沿用现有 `PublicVideoPublishRun`
- **业务操作事件**：如质量更新、物化、发布、回滚、前台命中，统一落到审计日志表

前端任务中心读取的是一个**聚合视图**，不是单一底层表。

## 4. 前端信息架构

新增统一入口：`运营工作台`

### 4.1 看板

展示明天最关键的运营状态：

- `P1 / P2 / P3` 模板数量
- 待复核模板数量
- 待转正式生成结果数量
- 今日发布数量
- 导入失败数量
- 今日前台命中数量

次级区域：

- 最近待处理事项
- 最近导入 / 发布 / 回滚 / 命中记录

### 4.2 质量分层

复用现有质量队列页面，新增：

- 角色禁用态
- 最近修改人、最近修改时间
- 更稳定的筛选项
- 运营备注展示

运营动作：

- 修改 `qualityTier`
- 修改 `reviewStatus`
- 修改 `qualityScore`
- 修改 `qualityReasons`
- 修改 `operatorNote`

### 4.3 生成结果库

展示 `GeneratedMakeupTemplate` 的运营视图：

- 生成结果 ID
- 场景、主风格、产品覆盖率
- 缺失品类
- 生成依据
- 是否已关联正式模板
- 已关联到哪个 `std_*`
- 当前正式模板状态

运营动作：

- 生成正式草稿
- 继续编辑正式模板
- 一键发布到正式模板库

### 4.4 统一任务中心

统一展示：

- 公有视频导入 run
- 生成结果物化
- 模板发布
- 模板回滚
- 前台命中

统一筛选维度：

- 类型
- 状态
- 时间
- 模板 ID
- 角色 / 操作者

## 5. 角色与权限模型

新增后端角色枚举：

```text
admin
operator
viewer
```

### 5.1 admin

允许：

- 质量分层修改
- 物化生成结果
- 发布正式模板
- 回滚正式模板
- 查看所有看板数据
- 查看所有任务
- 重试失败导入任务

### 5.2 operator

允许：

- 质量分层修改
- 物化生成结果
- 发起发布
- 查看统计和任务

不允许：

- 高风险回滚
- 系统级强制重试
- 角色配置

### 5.3 viewer

允许：

- 查看看板
- 查看模板
- 查看任务

不允许：

- 改质量结论
- 物化生成结果
- 发布
- 回滚

### 5.4 权限落点

后端通过：

- `BackofficeRole` 字段
- `BackofficeRoleGuard`
- `PolicyHelper`

对以下接口做保护：

- 质量分层写接口
- 生成结果物化接口
- 正式模板发布 / 回滚接口
- 导入任务重试接口

## 6. 后端数据设计

### 6.1 角色字段

在 `User` 主表增加角色字段，不放在 `UserSettings`。

原因：

- 角色属于权限域，不属于偏好配置
- 角色要被 guard 和 service 直接使用
- 角色应成为稳定的用户身份属性

### 6.2 审计日志

新增统一审计表，建议名：`TemplateOpsAuditLog`

核心字段：

- `id`
- `actorUserId`
- `actorRole`
- `eventType`
- `entityType`
- `entityId`
- `status`
- `summary`
- `payload`
- `createdAt`

首批事件类型：

- `quality_updated`
- `generated_materialized`
- `template_published`
- `template_rolled_back`
- `publish_retry`
- `recommendation_consumed`

用途：

- 任务中心聚合展示
- 审计回查
- 看板统计辅助

### 6.3 前台命中追踪

推荐成功后新增一条 `recommendation_consumed` 审计事件，最少记录：

- `userId`
- `recommendationId`
- `generatedTemplateId`
- `sourceStandardTemplateId`
- `sourceStandardTemplateVersionId`
- `templateTraceId`
- `scene`
- `styleTags`
- `productCoverageRate`
- `matchedAt`

目的：

- 证明前台已实际消费某正式模板
- 让运营能从后台回看命中链路

### 6.4 统一任务中心读模型

不新增统一任务执行器。

统一任务中心数据来自两部分：

1. `PublicVideoPublishRun`
   - 真实运行任务
   - 导入、抽帧、抽取、成稿、发布的 run 状态

2. `TemplateOpsAuditLog`
   - 业务操作事件
   - 物化、发布、回滚、命中等

聚合服务将这两部分统一映射成同一种前端响应格式：

- `type`
- `status`
- `title`
- `summary`
- `entityId`
- `actor`
- `createdAt`

## 7. 后端服务与接口

### 7.1 新增服务

1. `BackofficeAccessService`
   - 角色读取与权限判断

2. `TemplateOpsAuditService`
   - 统一写入运营审计事件

3. `OpsWorkbenchService`
   - 聚合看板与任务中心读模型

4. `OpsWorkbenchStatsService`
   - 看板统计数据聚合

### 7.2 新增接口

建议新增命名空间：

```text
/ops-workbench/*
```

首批接口：

- `GET /ops-workbench/summary`
  - 返回看板统计卡片数据

- `GET /ops-workbench/tasks`
  - 返回统一任务中心列表

- `GET /ops-workbench/pending`
  - 返回待处理事项列表

### 7.3 调整现有接口

以下接口保留原路径，但增加角色保护和审计：

- `PATCH /makeup-template-library/templates/:templateId/quality`
- `POST /makeup-template-library/generated-results/:templateId/materialize`
- `POST /makeup-template-library/generated-results/:templateId/publish`
- `POST /makeup-template-library/templates/:templateId/publish`
- `POST /makeup-template-library/templates/:templateId/rollback`
- `POST /makeup-template-library/ingestion/runs`

### 7.4 导入任务补充接口

当前已有：

- `POST /makeup-template-library/ingestion/runs`
- `GET /makeup-template-library/ingestion/runs`

明天可补：

- `GET /makeup-template-library/ingestion/runs/:runId`
- `POST /makeup-template-library/ingestion/runs/:runId/retry`

`retry` 仅 `admin` 可用。

## 8. 数据流

### 8.1 运营发布闭环

```text
生成结果 -> 物化为正式草稿 -> 编辑 -> 发布 -> 标记 P1/reviewed -> 前台推荐命中 -> 后台回查命中记录
```

### 8.2 导入任务闭环

```text
发起导入 -> PublicVideoPublishRun 运行 -> 成稿/发布 -> 工作台任务中心查看结果 -> 必要时重试失败任务
```

### 8.3 看板更新逻辑

看板不依赖离线 ETL，直接实时聚合：

- 正式模板表
- 生成结果表
- 导入 run 表
- 审计事件表

## 9. 错误处理

### 9.1 角色错误

- 无角色：按 `viewer` 处理或直接拒绝，具体以 demo 登录策略决定
- 越权操作：返回清晰 `403` 和可读错误信息

### 9.2 业务错误

- 生成结果不存在：返回 `404`
- 已关联但正式模板缺失：返回可读错误，并记录审计异常
- 发布失败：前端显示失败原因，不吞错
- 导入重试失败：任务中心显示失败状态和错误摘要

### 9.3 前端容错

- 看板加载失败：允许局部重试
- 任务中心加载失败：保留筛选条件并可重试
- viewer 角色操作按钮隐藏或禁用，不做假可点

## 10. 测试与验收

### 10.1 后端测试

必须覆盖：

- 角色 guard
- 权限边界
- 审计写入
- 看板聚合
- 任务中心聚合
- 命中追踪事件写入

### 10.2 前端测试

必须覆盖：

- 工作台 4 个主视图可打开
- viewer/operator/admin 按钮状态正确
- 质量分层保存成功后回显正确
- 生成结果可转正式草稿并跳详情页
- 发布后能看到任务记录

### 10.3 明天验收路径

1. 登录 `operator`
2. 进入 `运营工作台`
3. 在 `生成结果库` 选择一条生成结果
4. 生成正式草稿
5. 编辑并发布正式模板
6. 在 `质量分层` 标记为 `P1 + reviewed`
7. 在 `看板` 看到统计变化
8. 前台走推荐生成流程
9. 命中刚发布的正式模板
10. 回到 `任务中心`，看到：
   - 物化记录
   - 发布记录
   - 前台命中记录

满足以上 10 步，即视为“明天能稳定给运营/产品用”。

## 11. 实施边界与拆分建议

该设计适合拆成一个单独实现计划，但实现时应按以下顺序推进：

1. 角色与权限
2. 审计日志
3. 看板与任务中心读接口
4. 前端工作台入口与 4 个主视图
5. 前后台联调验收

这样能保证先把高风险权限边界落稳，再补工作台展示层。
