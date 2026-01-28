# Quick Fix Guide - All 3 Issues

## Current Status
✅ Code fixes are in place  
⚠️ Server needs to be restarted  
⚠️ MySQL.pdf needs to be re-processed

---

## Step 1: Restart the Server

**Stop any running server:**
- Press `Ctrl+C` in the terminal where the server is running
- Or close the terminal window

**Start the server from project root:**
```powershell
cd "E:\S Combinators"
.\venv\Scripts\python.exe -m uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000
```

**Or use the startup script:**
```powershell
.\scripts\start_backend.bat
```

**Verify server is running:**
- Open browser: http://localhost:8000/health
- Should see: `{"status": "ok"}`

---

## Step 2: Fix MySQL.pdf (Proxies Error)

The document was processed with old code. You need to re-process it:

**Option A: Delete and Re-upload (Recommended)**
1. In the Sources panel, click the delete/trash icon next to "MySQL.pdf"
2. Click "+ Add documents"
3. Upload MySQL.pdf again
4. It will process with the new fixed code

**Option B: Check Backend Logs**
- If the server is running, check the terminal for error messages
- The new code should automatically catch and fix the proxies error

---

## Step 3: Test Chat

After server restart:
1. Select a document (e.g., "Dog - Wikipedia.pdf")
2. Type a message in the chat
3. Should connect properly now

**If still failing:**
- Check browser console (F12 → Console) for errors
- Check backend terminal for error logs
- Verify CORS settings in `config/settings.py`

---

## Step 4: Test Quiz Generation

After server restart:
1. Select one or more documents
2. Click "Quiz" in the Studio panel
3. Should generate successfully

**If still failing:**
- Check backend logs for detailed error messages
- Verify OpenAI API key is set in `.env`
- Check if sources are properly indexed (should show "READY" status)

---

## Troubleshooting

### Server Won't Start
```powershell
# Check if port 8000 is in use
netstat -ano | findstr :8000

# Kill process if needed (replace PID with actual process ID)
taskkill /PID <PID> /F

# Then restart server
```

### Proxies Error Still Appears
The fix should catch it automatically. If not:
```powershell
# Try downgrading httpx
.\venv\Scripts\pip.exe install 'httpx<0.28.0'

# Or upgrade openai
.\venv\Scripts\pip.exe install --upgrade openai
```

### Chat/Studio Still Not Working
1. **Check server is actually running:**
   - Visit http://localhost:8000/api/docs
   - Should see API documentation

2. **Check browser console:**
   - Press F12 → Console tab
   - Look for CORS or connection errors

3. **Check backend logs:**
   - Look for `[STUDIO]`, `[ERROR]`, `[CHAT]` messages
   - Share logs if issues persist

---

## What Was Fixed

1. **Proxies Error:** Added try-catch that automatically uses httpx workaround
2. **Error Handling:** Enhanced logging in studio service
3. **Route Registration:** All routes are properly registered

---

## Next Steps

1. ✅ Restart server (Step 1)
2. ✅ Re-upload MySQL.pdf (Step 2)  
3. ✅ Test chat (Step 3)
4. ✅ Test quiz (Step 4)

**All fixes are in the code - just need server restart and re-processing MySQL.pdf!**
