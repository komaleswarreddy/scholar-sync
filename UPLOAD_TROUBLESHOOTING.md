# Upload Troubleshooting Guide

## Issue: Files Not Showing Up After Upload

### Fix Applied ✅

1. **Middleware Fix**: Updated to properly look up default tenant UUID from database
2. **Error Handling**: Improved frontend error handling
3. **Default Tenant**: Ensured default tenant exists in database

### Steps to Fix

1. **Restart Backend Server** (Required!)
   ```bash
   # Stop current server (Ctrl+C)
   cd backend
   python -m uvicorn app.main:app --reload
   ```

2. **Check Browser Console** (F12)
   - Look for any error messages
   - Check Network tab for API responses

3. **Test Upload Again**
   - Click "Add sources"
   - Select a PDF file
   - Wait for upload to complete
   - Check if file appears

### Debugging Steps

#### Check Backend Logs
Look at the terminal where backend is running for:
- Upload request received
- Processing steps
- Any errors

#### Check API Response
Open browser DevTools (F12) → Network tab:
1. Upload a file
2. Find the `/api/v1/ingest/upload` request
3. Check the response:
   - Status code (should be 200)
   - Response body (should have `id`, `title`, `status`)

#### Check List Sources
After upload, check:
1. Network tab → `/api/v1/ingest/sources` request
2. Response should have `sources` array
3. Your uploaded file should be in the array

### Common Issues

#### Issue 1: "Internal Server Error"
- **Cause**: Tenant UUID not found
- **Fix**: Restart backend (middleware fix applied)

#### Issue 2: "File type not supported"
- **Cause**: Only PDF and text files are supported
- **Fix**: Use `.pdf` or `.txt` files

#### Issue 3: Upload succeeds but file doesn't appear
- **Cause**: List sources API failing
- **Fix**: Check browser console for errors
- **Check**: Network tab for `/api/v1/ingest/sources` response

#### Issue 4: "Tenant not found"
- **Cause**: Default tenant missing
- **Fix**: Already fixed - default tenant is created automatically

### Testing the Fix

1. **Restart backend** (important!)
2. **Open browser** to http://localhost:3000
3. **Open DevTools** (F12) → Console tab
4. **Upload a PDF file**
5. **Check**:
   - Console for errors
   - Network tab for API calls
   - Sources list for your file

### Expected Behavior

1. Upload starts → "Uploading..." shows
2. File processes → Takes a few seconds
3. File appears in list → Should show immediately after upload completes
4. File is selectable → Can check the checkbox

### Still Not Working?

1. **Check backend terminal** for error messages
2. **Check browser console** (F12) for JavaScript errors
3. **Check Network tab** for failed API requests
4. **Try a small PDF file** (< 1MB) to rule out size issues


