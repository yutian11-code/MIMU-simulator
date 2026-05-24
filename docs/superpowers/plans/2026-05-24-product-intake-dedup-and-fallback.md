# Product Intake Dedup And Fallback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make product intake avoid duplicate user products and give users a clear path when local product lookup is weak or empty.

**Architecture:** Add a shared backend `ProductInventoryWriteService` in `user-products` so product-intake confirmations and manual user-product creation use the same create-or-merge path. Annotate scan candidates with whether the current user already owns them, then simplify the frontend intake result page so the top action is confirm/update and fallback entry supports text-assisted self-created drafts.

**Tech Stack:** NestJS, Prisma, Jest, Expo Router, React Native, TanStack Query.

---

### Task 1: Backend User Product Dedup Writer

**Files:**
- Create: `backend/src/user-products/product-inventory-write.service.ts`
- Modify: `backend/src/user-products/user-products.service.ts`
- Modify: `backend/src/user-products/user-products.module.ts`
- Test: `backend/src/user-products/product-inventory-write.service.spec.ts`

- [ ] Write failing Jest tests for creating a new user product and merging when the user already has an active/idle product with the same `productId`.
- [ ] Implement `ProductInventoryWriteService.upsertUserProduct()` with a return shape `{ userProduct, action }`, where `action` is `created` or `merged`.
- [ ] Refactor `UserProductsService.create()` to call the writer and return the mapped user product.
- [ ] Run `npm test -- product-inventory-write.service.spec.ts user-products.service.spec.ts`.

### Task 2: Product Intake Confirmation Uses Shared Writer

**Files:**
- Modify: `backend/src/product-intake/product-intake.service.ts`
- Modify: `backend/src/product-intake/dto/confirm-product-scan-response.dto.ts`
- Test: `backend/src/product-intake/product-intake.service.spec.ts`

- [ ] Add a failing test proving `confirmScan()` merges an existing user product instead of creating a duplicate.
- [ ] Inject `ProductInventoryWriteService` into `ProductIntakeService`.
- [ ] Return `dedupe: { action, existingUserProductId? }` from confirm responses.
- [ ] Run `npm test -- product-intake.service.spec.ts`.

### Task 3: Scan Candidate Inventory Status

**Files:**
- Modify: `backend/src/product-intake/product-intake.types.ts`
- Modify: `backend/src/product-intake/product-intake.mapper.ts`
- Modify: `backend/src/product-intake/dto/product-intake-candidate-response.dto.ts`
- Modify: `backend/src/product-intake/product-intake.service.ts`
- Test: `backend/src/product-intake/product-intake.service.spec.ts`

- [ ] Add a failing test proving candidates include `alreadyInInventory` and `existingUserProductId` when the user owns the matched product.
- [ ] Hydrate candidates after local matching by querying active/idle `UserProduct` rows for the authenticated user.
- [ ] Preserve existing scan mapping for old scans.
- [ ] Run `npm test -- product-intake.service.spec.ts`.

### Task 4: Frontend Intake Result Simplification

**Files:**
- Modify: `frontend/types/index.ts` or the actual type file that defines intake types.
- Modify: `frontend/app/assets/intake-result.tsx`

- [ ] Add candidate fields `alreadyInInventory?: boolean` and `existingUserProductId?: string`.
- [ ] Change the primary button label to `更新已有产品` when the selected candidate is already in inventory, otherwise `确认入库`.
- [ ] Make empty/weak results push users toward manual draft creation with a clear product-name/brand path instead of a dead empty state.
- [ ] Keep the existing confirm API payload shape so backend changes are compatible.

### Task 5: Verification

**Files:**
- Backend and frontend files changed above.

- [ ] Run focused backend tests.
- [ ] Run `npx tsc --noEmit` in `backend`.
- [ ] Run `npx tsc --noEmit` in `frontend` if the local dependency state allows it.
- [ ] Summarize any skipped verification and why.
