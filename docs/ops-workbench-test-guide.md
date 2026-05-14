# 运营工作台测试指引

## 1. 测试目标

验证明天给运营/产品演示时，下面这条链路可以闭环：

```text
生成结果 -> 质量分层 -> 正式模板发布 -> 前台推荐命中 -> 工作台回查
```

## 2. 前置条件

- 后端已启动，且数据库已完成最新 Prisma generate / migration。
- 前端已启动。
- 当前测试账号能正常登录。
- 当前账号角色已带 `role` 字段：
  - `admin`
  - `operator`
  - `viewer`

## 3. 入口

前端入口：

```text
个人档案 -> 运营工作台
```

工作台包含 4 个运营入口：

1. `质量分层`
2. `生成结果库`
3. `正式模板库`
4. `统一任务中心`

## 4. admin/operator 主链路

### 4.1 查看工作台看板

进入 `运营工作台` 后确认以下卡片能正常加载：

- `P1 模板`
- `P2 模板`
- `P3 模板`
- `待复核`
- `待转正式`
- `今日发布`
- `导入失败`
- `今日命中`

同时确认页面底部能看到 `最近动态`。

### 4.2 从生成结果库生成正式草稿

进入 `生成结果库`：

1. 找一条还未入正式库的 `GeneratedMakeupTemplate`
2. 点击 `生成正式草稿`
3. 应跳转到对应正式模板详情页

验收点：

- 页面跳转成功
- 能看到 `linkedStandardTemplateId`
- 生成结果页再次打开时，按钮应变成 `继续编辑正式模板`

### 4.3 正式模板编辑与发布

在模板详情页：

1. 修改模板名称、描述或步骤文案
2. 点击 `保存草稿`
3. 点击 `发布当前草稿`

验收点：

- 保存成功提示出现
- 发布成功后模板状态为 `published`
- `版本历史` 中可看到新的版本号

### 4.4 质量分层

进入 `质量分层`：

1. 找到刚发布的模板
2. 将 `qualityTier` 改为 `P1`
3. 将 `reviewStatus` 改为 `reviewed`
4. 填写简短 `运营备注`
5. 点击 `保存质量结论`

验收点：

- 保存成功
- 列表中该模板显示 `P1`
- 返回列表或刷新后结论仍存在

### 4.5 前台消费正式模板

走正常用户推荐链路：

1. 进入用户端推荐入口
2. 输入与该模板匹配的场景文案
3. 生成推荐

验收点：

- 推荐成功返回
- 响应中能看到 `generatedTemplateId`
- 如果已有正式模板链路，应能回查到标准模板来源

### 4.6 工作台回查

返回 `统一任务中心`：

确认最近任务里出现这些类型中的至少几项：

- `generated_materialized`
- `template_published`
- `quality_updated`
- `recommendation_consumed`

如果做过失败导入重试，还应看到：

- `publish_retry`

## 5. viewer 只读验证

使用 `viewer` 账号登录后验证：

1. 能进入 `运营工作台`
2. 能打开 `质量分层`、`生成结果库`、`正式模板库`、`统一任务中心`
3. 不能执行写操作

具体表现应为：

- 质量分层页按钮显示只读态
- 生成结果库不能物化/发布
- 模板详情不能保存/发布/归档
- 版本历史不能回滚

## 6. admin 专属验证

使用 `admin` 账号额外验证：

1. `版本历史` 中可执行回滚
2. `统一任务中心` 中失败导入任务可执行重试

## 7. 推荐的最小接口验收

### 7.1 工作台

```bash
curl -fsS http://127.0.0.1:13000/ops-workbench/summary -H "Authorization: Bearer $DEMO_TOKEN"
curl -fsS "http://127.0.0.1:13000/ops-workbench/tasks?limit=5" -H "Authorization: Bearer $DEMO_TOKEN"
curl -fsS http://127.0.0.1:13000/ops-workbench/pending -H "Authorization: Bearer $DEMO_TOKEN"
```

### 7.2 模板库

```bash
curl -fsS http://127.0.0.1:13000/makeup-template-library/quality-queue -H "Authorization: Bearer $DEMO_TOKEN"
curl -fsS http://127.0.0.1:13000/makeup-template-library/ingestion/runs -H "Authorization: Bearer $DEMO_TOKEN"
```

## 8. 明天演示时最重要的结论

如果以上链路都通过，可以明确对外说明：

1. 模板库不是静态 mock 页面，已经具备真实的正式模板运营能力。
2. 正式模板发布后的推荐消费可以被后台回查。
3. 运营、产品和查看者三类角色已经分层，不再是所有人都能直接发布/回滚。
