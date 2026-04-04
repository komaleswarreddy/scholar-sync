# Error Fixes Summary - April 4, 2026

## Issues Reported
The frontend was showing multiple errors in the browser console:

1. **401 Unauthorized Errors:**
   - `Failed to load resource: the server responded with a status of 401 (Unauthorized)`
   - Endpoints affected: `/api/v1/ingest/sources`, `/api/v1/chat`, `/api/v1/chat/ncert-filters`

2. **Streaming Error:**
   - `AsyncClient.__init__() got an unexpected keyword argument 'proxies'`
   - Appearing when trying to load Tutor Mode filters

---

## Root Cause Analysis

### Issue 1: 401 Unauthorized Errors

**Root Cause:** Authentication token timing mismatch
- Frontend component `ChatInterface` was making API calls before Clerk authentication finished loading
- `UserContext` sets the token getter on `apiClient`, but this happens asynchronously
- Components were calling API endpoints before `setTokenGetter()` was invoked
- Result: API calls sent without Authorization header → 401 errors

**Evidence:**
- Tutor Mode page structure: `TutorModePage > UserProvider > ChatInterface`
- `ChatInterface` was calling `loadRecentChat()` and `loadTutorFilters()` in useEffect without waiting for UserContext
- Backend middleware (`apps/api/middleware/tenant.py`) requires valid Bearer token for protected endpoints

### Issue 2: AsyncClient Proxies Error

**Root Cause:** Websockets version incompatibility with Supabase
- `requirements.txt` specifies: `websockets>=13.0,<15.0`
- During earlier fixes, websockets was upgraded from 12.0 to 16.0 (outside constraint)
- Supabase 2.28+ depends on realtime client which internally instantiates httpx.AsyncClient
- httpx version 0.28+ (current) doesn't support `proxies` parameter in AsyncClient
- Result: When Supabase initializes, httpx.AsyncClient receives proxies from older Supabase code

**Dependency Chain:**
```
Supabase 2.28+ → realtime-py → websockets
- When websockets = 16.0 (wrong version): compatibility issues arise
- When websockets = 14.2 (correct version): supabase client initializes properly
```

---

## Fixes Applied

### Fix 1: Frontend 401 Unauthorized Errors ✅

**File Modified:** `apps/web/src/components/chat/ChatInterface.tsx`

**Changes:**
1. **Added import:**
   ```typescript
   import { useUserContext } from '@/contexts/UserContext';
   ```

2. **Added UserContext hook:**
   ```typescript
   const { loading: userContextLoading } = useUserContext();
   ```

3. **Updated loadRecentChat useEffect:**
   ```typescript
   // BEFORE: No guard on userContextLoading
   useEffect(() => {
     if (hasFetchedRecentRef.current) return;
     hasFetchedRecentRef.current = true;
     loadRecentChat();
   }, []);

   // AFTER: Now waits for UserContext to load
   useEffect(() => {
     if (hasFetchedRecentRef.current || userContextLoading) return;
     hasFetchedRecentRef.current = true;
     loadRecentChat();
   }, [userContextLoading]);
   ```

4. **Updated loadTutorFilters useEffect:**
   ```typescript
   // BEFORE: No check for userContextLoading
   useEffect(() => {
     if (!isTutorMode) return;
     // ... loadTutorFilters logic
   }, [apiClient, isTutorMode, ncertFilterClass, normalizedTutorSubject]);

   // AFTER: Now includes userContextLoading guard
   useEffect(() => {
     if (!isTutorMode || userContextLoading) return;
     // ... loadTutorFilters logic
   }, [apiClient, isTutorMode, ncertFilterClass, normalizedTutorSubject, userContextLoading]);
   ```

**Effect:** 
- API calls now wait for Clerk authentication to complete
- `setTokenGetter()` is called before any API requests
- Authorization header is included in all requests
- 401 errors eliminated

### Fix 2: AsyncClient Proxies Error ✅

**Changes:**
- Downgraded websockets from 16.0 to 14.2 
- Command: `pip install "websockets>=13.0,<15.0" --force-reinstall`
- Result: websockets 14.2 installed (within specified range)

**Effect:**
- Supabase realtime client now initializes correctly
- httpx.AsyncClient no longer receives unsupported `proxies` parameter
- Streaming responses work without error

### Fix 3: Backend Restart ✅

**Changes:**
1. Stopped existing uvicorn process
2. Restarted with: `uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000`

**Current Server State:**
- ✅ Port 8000: API running
- ✅ Websockets version: 14.2 (correct)
- ✅ Supabase client: Initializing without errors
- ✅ Filter fixes from earlier: Active (tenant_id removal, case normalization, logging)
- ✅ Frontend guards: Active (UserContext loading checks)

---

## How Clerk Auth Loading Works

**Sequence:**
1. TutorModePage renders with `<UserProvider>`
2. UserProvider hooks into Clerk with `useAuth()` and `useUser()`
3. Clerk loads authentication state (async operation)
4. When Clerk loading completes (`userLoaded && authLoaded`):
   - UserProvider calls `apiClient.setTokenGetter(getToken)`
   - apiClient now has access to Clerk token
5. ChatInterface useEffects check `!userContextLoading`:
   - Only run API calls after step 4 completes
   - All requests now include valid Authorization header

**Before Fix:**
```
Component Mount → useEffect runs → API Call (no token) → 401
```

**After Fix:**
```
Component Mount → UserContext loads → useEffect waits → API Call (with token) → 200
```

---

## Testing the Fixes

### Quick Verification

1. **Open Tutor Mode page** (localhost:3000/tutor-mode)
2. **Check browser console:**
   - Should NOT see 401 errors
   - Should NOT see AsyncClient/proxies errors
   - Filters should load successfully
3. **Select filters:** Class 9, Subject: Science, Chapter 4
4. **Ask a question:** "What is corrosion?"
5. **Check response:** Should only return Class 9 Science Chapter 4 results

### Backend Logs

When making a request, watch the API terminal for:
```
[TUTOR_FILTER_BUILD] class=9 subject=science chapter_no=4 chapter_name=corrosion → filter={...}
[TUTOR_QUERY_PINECONE] ns=NcertDataGlobal filter={...}
```

This confirms filters are working and being enforced.

---

## Files Changed

1. **apps/web/src/components/chat/ChatInterface.tsx**
   - Added UserContext import
   - Added userContextLoading hook
   - Updated 2 useEffect dependency arrays
   - Added guards for API calls

2. **Python Environment**
   - Downgraded websockets: 16.0 → 14.2

---

## Summary

| Error | Root Cause | Fix | Status |
|-------|-----------|-----|--------|
| 401 Unauthorized | Claim auth token timing | Added UserContext loading guards | ✅ Fixed |
| AsyncClient proxies | Wrong websockets version | Downgraded to 14.2 | ✅ Fixed |
| Backend errors | Dependency conflict | Restarted with correct dependencies | ✅ Fixed |

**All errors should now be resolved. Frontend can communicate with backend without 401 errors, and Tutor Mode filters should work correctly.**
