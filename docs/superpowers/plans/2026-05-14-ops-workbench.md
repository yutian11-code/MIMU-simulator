# Ops Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a stable backoffice workbench that lets admin/operator/viewer users complete the chain `generated result -> quality review -> formal publish/rollback -> recommendation consumption trace -> workbench lookup` without touching the database.

**Architecture:** Extend the existing template-library and generated-result platform instead of replacing it. Add a light RBAC layer on `User`, persist business operations in a dedicated ops audit table, expose a dedicated `ops-workbench` backend read model that aggregates audit logs and public-video ingestion runs, then wire a new frontend workbench entry and role-aware management screens on top of the current template-library pages.

**Tech Stack:** NestJS 11, Prisma 7, PostgreSQL, Jest, Expo Router 6, React Native, Zustand, TanStack Query.

---

## File Map

### Backend schema and auth
- Modify: `backend/prisma/schema.prisma`
- Create: `backend/prisma/migrations/20260514153000_add_ops_workbench_rbac_and_audit/migration.sql`
- Modify: `backend/src/common/auth/authenticated-user.type.ts`
- Modify: `backend/src/common/auth/demo-auth.guard.ts`
- Create: `backend/src/common/auth/backoffice-role.decorator.ts`
- Create: `backend/src/common/auth/backoffice-role.guard.ts`
- Create: `backend/src/common/auth/backoffice-role.guard.spec.ts`
- Create: `backend/src/auth/auth.service.spec.ts`
- Modify: `backend/src/auth/auth.service.ts`
- Modify: `backend/src/auth/dto/login-response.dto.ts`
- Modify: `backend/src/users/user.mapper.ts`
- Modify: `backend/src/users/dto/user-response.dto.ts`
- Modify: `backend/src/users/users.service.ts`

### Backend ops audit and workbench APIs
- Create: `backend/src/makeup-templates/template-library/template-ops-audit.service.ts`
- Create: `backend/src/makeup-templates/template-library/template-ops-audit.service.spec.ts`
- Modify: `backend/src/makeup-templates/template-library/template-quality.service.ts`
- Modify: `backend/src/makeup-templates/template-library/generated-template-publication.service.ts`
- Modify: `backend/src/makeup-templates/template-library/template-library-admin.service.ts`
- Modify: `backend/src/recommendations/recommendations.service.ts`
- Modify: `backend/src/makeup-templates/template-library/public-video-ingestion/public-video-ingestion.service.ts`
- Modify: `backend/src/makeup-templates/template-library/public-video-ingestion/public-video-publish.service.ts`
- Create: `backend/src/ops-workbench/dto/query-ops-workbench-tasks.dto.ts`
- Create: `backend/src/ops-workbench/ops-workbench.service.ts`
- Create: `backend/src/ops-workbench/ops-workbench.controller.ts`
- Create: `backend/src/ops-workbench/ops-workbench.module.ts`
- Create: `backend/src/ops-workbench/ops-workbench.service.spec.ts`
- Create: `backend/src/ops-workbench/ops-workbench.controller.spec.ts`
- Modify: `backend/src/makeup-templates/template-library/template-library.controller.ts`
- Modify: `backend/src/makeup-templates/template-library/template-library.controller.spec.ts`
- Modify: `backend/src/app.module.ts`

### Frontend workbench and role-aware access
- Modify: `frontend/types/user.ts`
- Modify: `frontend/store/demo-store.ts`
- Modify: `frontend/app/_layout.tsx`
- Modify: `frontend/app/(tabs)/profile.tsx`
- Create: `frontend/types/ops-workbench.ts`
- Create: `frontend/services/opsWorkbenchService.ts`
- Create: `frontend/app/ops-workbench/index.tsx`
- Create: `frontend/app/ops-workbench/tasks.tsx`
- Modify: `frontend/types/template-library.ts`
- Modify: `frontend/services/templateLibraryService.ts`
- Modify: `frontend/app/template-library/index.tsx`
- Modify: `frontend/app/template-library/quality-queue.tsx`
- Modify: `frontend/app/template-library/generated.tsx`

### Docs and validation
- Modify: `docs/template-matching-test-guide.md`
- Create: `docs/ops-workbench-test-guide.md`

## Task 1: Add RBAC foundation and propagate role through auth

**Files:**
- Modify: `backend/prisma/schema.prisma`
- Create: `backend/prisma/migrations/20260514153000_add_ops_workbench_rbac_and_audit/migration.sql`
- Modify: `backend/src/common/auth/authenticated-user.type.ts`
- Modify: `backend/src/common/auth/demo-auth.guard.ts`
- Create: `backend/src/auth/auth.service.spec.ts`
- Create: `backend/src/common/auth/backoffice-role.guard.spec.ts`
- Modify: `backend/src/auth/auth.service.ts`
- Modify: `backend/src/auth/dto/login-response.dto.ts`
- Modify: `backend/src/users/user.mapper.ts`
- Modify: `backend/src/users/dto/user-response.dto.ts`
- Modify: `backend/src/users/users.service.ts`

- [ ] **Step 1: Write failing auth and guard tests**

```ts
it('returns role in login payload and getMe profile', async () => {
  prisma.user.findUnique.mockResolvedValue({
    id: 'user-001',
    nickname: 'Mia',
    skinType: 'combination',
    makeupPreference: 'natural',
    commonScenarios: ['通勤'],
    role: 'operator',
  });

  await expect(service.login('test')).resolves.toMatchObject({
    user: { id: 'user-001', role: 'operator' },
  });
});

it('allows admin for operator endpoints and rejects viewer', async () => {
  expect(
    guard.canActivate(buildContext({ user: { id: 'u1', role: 'admin' } })),
  ).resolves.toBe(true);

  await expect(
    guard.canActivate(buildContext({ user: { id: 'u2', role: 'viewer' } })),
  ).rejects.toThrow('Forbidden');
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && npm test -- auth.service.spec.ts backoffice-role.guard.spec.ts --runInBand`
Expected: FAIL because `role` is absent from schema/auth mapping and the role guard does not exist.

- [ ] **Step 3: Add Prisma enum and user field**

```prisma
enum BackofficeRole {
  admin
  operator
  viewer
}

model User {
  id               String         @id @db.VarChar(50)
  role             BackofficeRole @default(viewer)
}
```

- [ ] **Step 4: Propagate role through backend auth and user mapping**

```ts
export type AuthenticatedUser = {
  id: string;
  role: 'admin' | 'operator' | 'viewer';
};
```

```ts
const user = await this.prisma.user.findUnique({
  where: { id: getDemoUserId() },
  select: { id: true, role: true },
});
request.user = user;
```

```ts
export function mapUserProfile(user: User) {
  return {
    id: user.id,
    nickname: user.nickname,
    skinType: user.skinType,
    makeupPreference: user.makeupPreference,
    commonScenarios: user.commonScenarios,
    role: user.role,
  };
}
```

- [ ] **Step 5: Add role decorator and guard**

```ts
export const BackofficeRoles = (...roles: BackofficeRole[]) =>
  SetMetadata(BACKOFFICE_ROLE_KEY, roles);
```

```ts
if (!allowedRoles.includes(request.user.role)) {
  throw new ForbiddenException('Backoffice role is not allowed');
}
```

- [ ] **Step 6: Run Prisma generate and backend auth tests**

Run: `cd backend && npm run prisma:generate && npm test -- auth.service.spec.ts backoffice-role.guard.spec.ts --runInBand`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
cd backend
git add prisma/schema.prisma prisma/migrations src/common/auth src/auth src/users
git commit -m "feat: add backoffice role foundation"
```

## Task 2: Persist ops audit events and protect write endpoints

**Files:**
- Modify: `backend/prisma/schema.prisma`
- Modify: `backend/prisma/migrations/20260514153000_add_ops_workbench_rbac_and_audit/migration.sql`
- Create: `backend/src/makeup-templates/template-library/template-ops-audit.service.ts`
- Create: `backend/src/makeup-templates/template-library/template-ops-audit.service.spec.ts`
- Modify: `backend/src/makeup-templates/template-library/template-quality.service.ts`
- Modify: `backend/src/makeup-templates/template-library/generated-template-publication.service.ts`
- Modify: `backend/src/makeup-templates/template-library/template-library-admin.service.ts`
- Modify: `backend/src/recommendations/recommendations.service.ts`
- Modify: `backend/src/makeup-templates/template-library/template-library.controller.ts`
- Modify: `backend/src/makeup-templates/template-library/template-library.controller.spec.ts`

- [ ] **Step 1: Write failing tests for audit writes and endpoint protection**

```ts
it('records quality_updated when template quality changes', async () => {
  await service.updateTemplateQuality('std_tpl_001', 'user-001', {
    qualityTier: 'P1',
    qualityScore: 91,
    qualityReasons: ['five-step complete'],
    reviewStatus: 'reviewed',
  });

  expect(prisma.templateOpsAuditLog.create).toHaveBeenCalledWith(
    expect.objectContaining({
      data: expect.objectContaining({
        eventType: 'quality_updated',
        entityType: 'standard_template',
        entityId: 'std_tpl_001',
      }),
    }),
  );
});

it('requires operator-or-above for materialize and publish endpoints', async () => {
  expectReflectRoles('generated-results/:templateId/materialize').toEqual([
    'admin',
    'operator',
  ]);
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && npm test -- template-ops-audit.service.spec.ts template-library.controller.spec.ts --runInBand`
Expected: FAIL because audit persistence and role metadata are not present.

- [ ] **Step 3: Add audit enum and table**

```prisma
enum TemplateOpsEventType {
  quality_updated
  generated_materialized
  template_published
  template_rolled_back
  publish_retry
  recommendation_consumed
}

model TemplateOpsAuditLog {
  id          String               @id @db.VarChar(64)
  actorUserId String               @map("actor_user_id") @db.VarChar(50)
  actorRole   BackofficeRole       @map("actor_role")
  eventType   TemplateOpsEventType @map("event_type")
  entityType  String               @map("entity_type") @db.VarChar(40)
  entityId    String               @map("entity_id") @db.VarChar(90)
  status      String               @db.VarChar(30)
  summary     String               @db.VarChar(255)
  payload     Json                 @default("{}")
  createdAt   DateTime             @default(now()) @map("created_at")
}
```

- [ ] **Step 4: Implement reusable audit writer**

```ts
await this.prisma.templateOpsAuditLog.create({
  data: {
    id: `tops_${randomUUID().slice(0, 12)}`,
    actorUserId,
    actorRole,
    eventType,
    entityType,
    entityId,
    status,
    summary,
    payload,
  },
});
```

- [ ] **Step 5: Wire audit writes into business services**

```ts
await this.audit.log({
  actorUserId: userId,
  actorRole: userRole,
  eventType: 'generated_materialized',
  entityType: 'generated_template',
  entityId: templateId,
  status: linkedTemplate.status,
  summary: `Materialized ${templateId} to ${linkedTemplate.id}`,
  payload: { linkedStandardTemplateId: linkedTemplate.id },
});
```

```ts
await this.audit.logRecommendationConsumed({
  actorUserId: userId,
  actorRole: 'viewer',
  generatedTemplateId: template.id,
  standardTemplateId: template.linkedStandardTemplateId ?? template.sourceStandardTemplateId,
  recommendationId: recommendation.id,
});
```

- [ ] **Step 6: Protect write endpoints with role guard**

```ts
@UseGuards(DemoAuthGuard, BackofficeRoleGuard)
@BackofficeRoles('admin', 'operator')
@Patch('templates/:templateId/quality')
```

```ts
@BackofficeRoles('admin')
@Post('templates/:templateId/rollback')
```

- [ ] **Step 7: Run targeted tests**

Run: `cd backend && npm test -- template-ops-audit.service.spec.ts template-library.controller.spec.ts template-quality.service.spec.ts generated-template-publication.service.spec.ts recommendations.service.spec.ts --runInBand`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
cd backend
git add prisma/schema.prisma prisma/migrations src/makeup-templates/template-library src/recommendations
git commit -m "feat: add ops audit logging and protected template actions"
```

## Task 3: Add ops workbench backend read model and ingestion task APIs

**Files:**
- Create: `backend/src/ops-workbench/dto/query-ops-workbench-tasks.dto.ts`
- Create: `backend/src/ops-workbench/ops-workbench.service.ts`
- Create: `backend/src/ops-workbench/ops-workbench.controller.ts`
- Create: `backend/src/ops-workbench/ops-workbench.module.ts`
- Create: `backend/src/ops-workbench/ops-workbench.service.spec.ts`
- Create: `backend/src/ops-workbench/ops-workbench.controller.spec.ts`
- Modify: `backend/src/makeup-templates/template-library/public-video-ingestion/public-video-ingestion.service.ts`
- Modify: `backend/src/makeup-templates/template-library/public-video-ingestion/public-video-publish.service.ts`
- Modify: `backend/src/makeup-templates/template-library/template-library.controller.ts`
- Modify: `backend/src/app.module.ts`

- [ ] **Step 1: Write failing service tests for summary and unified tasks**

```ts
it('aggregates summary counts for dashboard cards', async () => {
  prisma.standardMakeupTemplate.count
    .mockResolvedValueOnce(12)
    .mockResolvedValueOnce(8)
    .mockResolvedValueOnce(4)
    .mockResolvedValueOnce(6);
  prisma.generatedMakeupTemplate.count.mockResolvedValue(5);
  prisma.templateOpsAuditLog.count.mockResolvedValue(3);

  await expect(service.getSummary()).resolves.toEqual(
    expect.objectContaining({
      qualityTierCounts: { P1: 12, P2: 8, P3: 4 },
      pendingReviewCount: 6,
      pendingGeneratedCount: 5,
      todaysRecommendationConsumedCount: 3,
    }),
  );
});

it('returns ingestion runs and audit events in one task list ordered by time', async () => {
  const result = await service.listTasks({ type: 'all', limit: 20 });
  expect(result.items[0]).toMatchObject({
    kind: expect.stringMatching(/ingestion_run|audit_event/),
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && npm test -- ops-workbench.service.spec.ts ops-workbench.controller.spec.ts --runInBand`
Expected: FAIL because the module and APIs do not exist.

- [ ] **Step 3: Implement summary and task aggregation service**

```ts
const [p1, p2, p3, pendingReviewCount, pendingGeneratedCount, todaysConsumedCount] =
  await Promise.all([
    this.prisma.standardMakeupTemplate.count({ where: { qualityTier: 'P1' } }),
    this.prisma.standardMakeupTemplate.count({ where: { qualityTier: 'P2' } }),
    this.prisma.standardMakeupTemplate.count({ where: { qualityTier: 'P3' } }),
    this.prisma.standardMakeupTemplate.count({
      where: { qualityReviewStatus: 'pending' },
    }),
    this.prisma.generatedMakeupTemplate.count({
      where: { linkedStandardTemplateId: null },
    }),
    this.prisma.templateOpsAuditLog.count({
      where: {
        eventType: 'recommendation_consumed',
        createdAt: { gte: startOfDay },
      },
    }),
  ]);
```

```ts
return {
  items: [...mapRunTasks(runs), ...mapAuditTasks(events)]
    .sort((a, b) => +new Date(b.createdAt) - +new Date(a.createdAt))
    .slice(0, limit),
};
```

- [ ] **Step 4: Expose controller endpoints**

```ts
@Get('ops-workbench/summary')
getSummary() {}

@Get('ops-workbench/tasks')
listTasks(@Query() query: QueryOpsWorkbenchTasksDto) {}

@Get('ops-workbench/pending')
listPending() {}
```

- [ ] **Step 5: Add run detail and retry endpoints on template-library ingestion routes**

```ts
@Get('ingestion/runs/:runId')
getPublicVideoIngestionRun(@Param('runId') runId: string) {}

@Post('ingestion/runs/:runId/retry')
@BackofficeRoles('admin')
retryPublicVideoIngestionRun(@Param('runId') runId: string) {}
```

```ts
async retryRun(runId: string, ownerUserId: string) {
  const existing = await this.getRun(runId);
  return this.ingestFromManifest({
    manifestPath: existing?.manifestPath,
    ownerUserId,
    triggerSource: `retry:${runId}`,
  });
}
```

- [ ] **Step 6: Register module and run backend integration tests**

Run: `cd backend && npm test -- ops-workbench.service.spec.ts ops-workbench.controller.spec.ts template-library.controller.spec.ts --runInBand`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
cd backend
git add src/ops-workbench src/makeup-templates/template-library/public-video-ingestion src/app.module.ts
git commit -m "feat: add ops workbench backend read model"
```

## Task 4: Build the frontend ops workbench and role-aware management surfaces

**Files:**
- Modify: `frontend/types/user.ts`
- Modify: `frontend/store/demo-store.ts`
- Modify: `frontend/app/_layout.tsx`
- Modify: `frontend/app/(tabs)/profile.tsx`
- Create: `frontend/types/ops-workbench.ts`
- Create: `frontend/services/opsWorkbenchService.ts`
- Create: `frontend/app/ops-workbench/index.tsx`
- Create: `frontend/app/ops-workbench/tasks.tsx`
- Modify: `frontend/types/template-library.ts`
- Modify: `frontend/services/templateLibraryService.ts`
- Modify: `frontend/app/template-library/index.tsx`
- Modify: `frontend/app/template-library/quality-queue.tsx`
- Modify: `frontend/app/template-library/generated.tsx`

- [ ] **Step 1: Write the failing type and service surface**

```ts
export type BackofficeRole = 'admin' | 'operator' | 'viewer';

export type OpsWorkbenchSummary = {
  qualityTierCounts: { P1: number; P2: number; P3: number };
  pendingReviewCount: number;
  pendingGeneratedCount: number;
  todayPublishedCount: number;
  failedIngestionCount: number;
  todaysRecommendationConsumedCount: number;
};
```

```ts
export const opsWorkbenchService = {
  getSummary: () => apiRequest<OpsWorkbenchSummary>('/ops-workbench/summary'),
  listTasks: (query = {}) =>
    apiRequest<{ items: OpsWorkbenchTask[] }>('/ops-workbench/tasks', { query }),
};
```

- [ ] **Step 2: Run frontend typecheck to see current missing symbols**

Run: `cd frontend && npx tsc --noEmit`
Expected: FAIL after adding new route/service imports until the screens are implemented.

- [ ] **Step 3: Add workbench route entry and dashboard screen**

```tsx
<Stack.Screen name="ops-workbench" />
```

```tsx
<QuickEntry
  icon="briefcase-outline"
  title="运营工作台"
  description="统一处理质量分层、生成结果发布和任务回查。"
  onPress={() => router.push('/ops-workbench' as Href)}
/>
```

```tsx
const canOperate = currentUser?.role === 'admin' || currentUser?.role === 'operator';
const canRollback = currentUser?.role === 'admin';
```

- [ ] **Step 4: Build dashboard cards and task list screen**

```tsx
const summaryQuery = useQuery({
  queryKey: ['ops-workbench-summary'],
  queryFn: () => opsWorkbenchService.getSummary(),
});

const tasksQuery = useQuery({
  queryKey: ['ops-workbench-tasks', filter],
  queryFn: () => opsWorkbenchService.listTasks(filter),
});
```

```tsx
<ActionCard
  title="质量分层"
  description="维护 P1 / P2 / P3 与复核结论"
  onPress={() => router.push('/template-library/quality-queue' as Href)}
/>
```

- [ ] **Step 5: Make existing template-library pages role-aware**

```tsx
<ActionButton
  label="生成正式草稿"
  disabled={!canOperate || materializeMutation.isPending}
  onPress={() => materializeMutation.mutate(item.id)}
/>
```

```tsx
{!canOperate ? (
  <Text className="text-[12px] text-[#8C817B]">当前账号只有查看权限。</Text>
) : null}
```

```tsx
<ActionButton
  label="回滚到该版本"
  disabled={!canRollback}
  onPress={() => rollbackMutation.mutate({ sourceVersionId: version.id })}
/>
```

- [ ] **Step 6: Run frontend validation**

Run: `cd frontend && npx tsc --noEmit && npm run lint`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
cd frontend
git add app services store types
git commit -m "feat: add ops workbench frontend"
```

## Task 5: Validate the user journey and document tomorrow’s runbook

**Files:**
- Modify: `docs/template-matching-test-guide.md`
- Create: `docs/ops-workbench-test-guide.md`

- [ ] **Step 1: Document the tomorrow-critical user journey**

```md
1. 使用 admin/operator 账号登录，进入“我的” -> “运营工作台”
2. 在“生成结果库”确认未物化结果，点击“生成正式草稿”
3. 跳转模板详情，补充描述后发布
4. 在“质量分层”把模板设为 `P1 + reviewed`
5. 在前台生成推荐，确认命中该模板
6. 回到“统一任务中心”，确认出现 `template_published` 与 `recommendation_consumed`
```

- [ ] **Step 2: Run backend verification suite**

Run: `cd backend && npm run prisma:generate && npm run build && npm test -- auth.service.spec.ts backoffice-role.guard.spec.ts template-ops-audit.service.spec.ts template-quality.service.spec.ts generated-template-publication.service.spec.ts recommendations.service.spec.ts ops-workbench.service.spec.ts ops-workbench.controller.spec.ts template-library.controller.spec.ts --runInBand`
Expected: PASS.

- [ ] **Step 3: Run frontend verification suite**

Run: `cd frontend && npx tsc --noEmit && npm run lint`
Expected: PASS.

- [ ] **Step 4: Smoke-check the full chain manually**

Run:

```bash
curl -fsS http://127.0.0.1:13000/ops-workbench/summary -H "Authorization: Bearer $DEMO_TOKEN"
curl -fsS "http://127.0.0.1:13000/ops-workbench/tasks?limit=5" -H "Authorization: Bearer $DEMO_TOKEN"
curl -fsS http://127.0.0.1:13000/makeup-template-library/quality-queue -H "Authorization: Bearer $DEMO_TOKEN"
```

Expected: three APIs return JSON with non-empty structures and no auth errors.

- [ ] **Step 5: Commit**

```bash
git add docs/template-matching-test-guide.md docs/ops-workbench-test-guide.md
git commit -m "docs: add ops workbench verification guide"
```

## Self-Review

### Spec coverage
- 权限与角色：Task 1 and Task 2.
- 运营统计看板：Task 3 backend summary + Task 4 dashboard.
- 统一任务中心：Task 3 aggregation API + Task 4 task screen.
- 质量分层稳定可用：Task 2 protection/audit + Task 4 role-aware queue.
- 生成结果转正式模板稳定可用：Task 2 audit/protection + Task 4 generated library actions.
- 前台推荐消费并可后台回查：Task 2 recommendation audit + Task 3 task aggregation + Task 5 smoke validation.

### Placeholder scan
- Migration path is fixed.
- All new APIs and core file paths are concrete.
- No `TODO` or `TBD` markers remain.

### Type consistency
- Role enum is consistently `admin | operator | viewer`.
- Audit events are consistently `quality_updated | generated_materialized | template_published | template_rolled_back | publish_retry | recommendation_consumed`.
- Workbench API surface is consistently `summary`, `tasks`, `pending`, plus ingestion `GET /:runId` and `POST /:runId/retry`.

Plan complete and saved to `docs/superpowers/plans/2026-05-14-ops-workbench.md`. Execution choice is already fixed by the latest user request: proceed with subagent-driven implementation.
