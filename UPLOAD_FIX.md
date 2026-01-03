# Upload Issue Fix

## Problem
Files were not showing up after upload because:
1. The middleware was using a hardcoded string `"default-tenant-id"` instead of a real UUID
2. The tenant lookup wasn't working properly for localhost
3. The default tenant might not exist in the database

## Fix Applied

1. **Updated middleware** to:
   - Look up the actual "default" tenant from database
   - Create it if it doesn't exist
   - Use the real tenant UUID

2. **Improved error handling** in frontend:
   - Better error logging
   - Graceful fallback if API fails

3. **Ensured default tenant exists** in database

## Testing

After restarting the backend, try uploading again:
1. Click "Add sources"
2. Select a PDF file
3. Wait for upload
4. Check if file appears in the list

If it still doesn't work, check:
- Browser console (F12) for errors
- Backend terminal for error messages
- Network tab to see API responses


