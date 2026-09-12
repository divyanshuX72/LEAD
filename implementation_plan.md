# Fix Lead Dashboard Integration

This plan details the steps required to resolve the Lead Dashboard's `404` errors and the `undefined` batch ID bug, fully unifying the frontend and backend without modifying the Lead Search behavior or logic.

## Open Questions

None currently. The root causes of the `404`s and `undefined` ID have been fully identified.

## Proposed Changes

---

### Backend Router Fixes

The frontend expects endpoints under `/api/v1/leads/...`, but the backend `leads.py` router was mounted without the `/leads` prefix.

#### [MODIFY] [leads.py](file:///c:/Users/mrhyp/Downloads/lead/backend/platform_app/api/routers/leads.py)
- Add `prefix="/leads"` to the `APIRouter` initialization:
  `router = APIRouter(prefix="/leads", tags=["Lead Agent"])`

### Undefined Batch ID Fix

When starting a search, the backend `lead_search.py` kicks off a background task but does not return the `batch_id` synchronously. The frontend expects a `batch_id` in the JSON response, and stores `undefined` when it's missing, leading to polling `/lead-batches/undefined`.

#### [MODIFY] [lead_discovery_orchestrator.py](file:///c:/Users/mrhyp/Downloads/lead/backend/platform_app/services/lead_discovery_orchestrator.py)
- Make `_create_batch` a public method: `create_batch`.
- Update `run_discovery` to accept `batch: LeadBatch` instead of creating the batch itself. This allows the API to create the batch first, get the ID, and then start the background job.

#### [MODIFY] [lead_search.py](file:///c:/Users/mrhyp/Downloads/lead/backend/platform_app/api/routers/lead_search.py)
- Call `orchestrator.create_batch(...)` synchronously to obtain the `batch_id`.
- Launch `orchestrator.run_discovery(batch=batch, ...)` in `background_tasks`.
- Add `"batch_id": batch.id` to the returned JSON response so the frontend receives it correctly.

### Dashboard Stats Fix (Empty State)

The `/dashboard/stats` endpoint currently might fail or return `None` for `last_search` if there are no batches. We need to ensure it returns cleanly on empty databases without `404`ing or crashing.

#### [MODIFY] [leads.py](file:///c:/Users/mrhyp/Downloads/lead/backend/platform_app/api/routers/leads.py)
- Review `get_dashboard_stats` to make sure it gracefully handles `None` for dates when there are zero batches. It appears mostly correct, but will double-check.

### Frontend API Polling Loop Prevention

React Query defaults to retrying failed requests (like `404`s) exponentially, which causes a retry storm in the browser console.

#### [MODIFY] [client.ts](file:///c:/Users/mrhyp/Downloads/lead/frontend/src/api/client.ts) (or React Query setup)
- Ensure React Query doesn't indefinitely retry deterministic `404` errors. (Will modify `QueryClient` default options).

## Verification Plan

### Manual Verification
1. Open the UI, navigate to Lead Search.
2. Enter keywords (e.g. "dental doctor") and location (e.g. "Mumbai"), target "10".
3. Check the Network tab to ensure `POST /api/v1/leads/search` returns `200` with `batch_id`.
4. Ensure no `GET /api/v1/leads/lead-batches/undefined` requests are made.
5. Watch the dashboard to ensure the batch appears immediately in the "Running" state.
6. Verify Dashboard stats load without `404`.
7. Once search completes, verify the batch status updates and opening the batch shows the leads.
8. Verify Export to CSV works correctly.
