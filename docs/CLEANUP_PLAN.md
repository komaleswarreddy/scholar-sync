# Backend Cleanup Plan

## Overview

This document outlines the cleanup plan to remove the old `backend/` folder and migrate all configuration files to the new project structure.

## Current State

### Old Structure (to be removed)
- `backend/` - Legacy backend code
  - `backend/app/` - Old application code
  - `backend/venv/` - Old virtual environment
  - `backend/requirements.txt` - Old dependencies
  - `backend/Dockerfile` - Old Dockerfile
  - `backend/alembic.ini` - Old Alembic config
  - `backend/.env` - Environment variables (⚠️ **PRESERVE**)
  - `backend/.env.bak` - Backup env file (⚠️ **PRESERVE**)

### New Structure (target)
- `apps/api/` - New API application ✅
- `packages/core/` - Core packages ✅
- `config/` - Configuration ✅
- `requirements.txt` - Root level ✅
- `Dockerfile.api` - Updated Dockerfile ✅
- `alembic.ini` - Root level ✅
- `scripts/` - Startup scripts ✅

## Migration Steps

### ✅ Step 1: Update Configuration Files (COMPLETED)

1. **Dockerfile**
   - ✅ Created `Dockerfile.api` at root
   - ✅ Updated CMD to use `apps.api.main:app`
   - ✅ Updated COPY paths

2. **Requirements**
   - ✅ Moved `requirements.txt` to root
   - ✅ All dependencies preserved

3. **Alembic**
   - ✅ Created `alembic.ini` at root
   - ✅ Updated `script_location` to `packages/core/database/migrations`

4. **Start Scripts**
   - ✅ Updated `scripts/start_backend.sh`
   - ✅ Updated to use `apps.api.main:app`

### ⚠️ Step 2: Preserve Critical Files

**BEFORE DELETING `backend/`, preserve these files:**

1. **Environment Variables**
   ```bash
   # Copy .env files to root (if not already there)
   cp backend/.env .env  # If .env doesn't exist at root
   cp backend/.env.bak .env.bak  # If needed
   ```

2. **Virtual Environment** (optional)
   - The old `backend/venv/` can be deleted
   - Create new venv at root: `python -m venv venv`

3. **Migrations** (if any custom ones)
   - Check `backend/migrations/` for custom SQL files
   - These should be in `packages/core/database/migrations/`

### ⚠️ Step 3: Verify New Structure Works

**Before deleting, verify:**

1. **Import Verification** ✅
   ```bash
   python3 scripts/check_import_syntax.py
   python3 scripts/check_circular_deps.py
   ```

2. **Test API Startup**
   ```bash
   # Activate venv
   source venv/bin/activate  # or backend/venv/bin/activate
   
   # Test import
   python -c "from apps.api.main import app; print('✓ Import successful')"
   
   # Test startup (don't run, just check syntax)
   python -m uvicorn apps.api.main:app --help
   ```

3. **Check Database Connection**
   ```bash
   python scripts/init_db.py  # Should work with new paths
   ```

### ⚠️ Step 4: Backup Before Deletion

**Create backup of backend folder:**
```bash
# Create backup (optional but recommended)
tar -czf backend_backup_$(date +%Y%m%d).tar.gz backend/
```

### ⚠️ Step 5: Delete Old Backend Folder

**After verification, delete:**
```bash
# Remove old backend folder
rm -rf backend/
```

**OR if you want to be extra safe:**
```bash
# Move to trash first
mv backend/ ~/.Trash/backend_old_$(date +%Y%m%d)
```

## Files to Preserve

### Must Preserve
- `backend/.env` → Copy to root `.env` (if not exists)
- `backend/.env.bak` → Copy to root `.env.bak` (if needed)

### Already Migrated
- ✅ `backend/requirements.txt` → `requirements.txt` (root)
- ✅ `backend/Dockerfile` → `Dockerfile.api` (root)
- ✅ `backend/alembic.ini` → `alembic.ini` (root)
- ✅ `backend/scripts/` → `scripts/` (root)
- ✅ `backend/app/` → `apps/api/` + `packages/core/`

### Can Delete
- ❌ `backend/venv/` - Old virtual environment
- ❌ `backend/app/` - Old application code
- ❌ `backend/migrations/` - Old migrations (if new ones exist)

## Verification Checklist

Before deleting `backend/`:

- [ ] ✅ New structure files created
- [ ] ✅ Configuration files updated
- [ ] ✅ Import verification passed
- [ ] ✅ Environment variables preserved
- [ ] ✅ Backup created (optional)
- [ ] ⚠️ **Test API startup** (recommended)
- [ ] ⚠️ **Test database connection** (recommended)
- [ ] ⚠️ **Test at least one API endpoint** (recommended)

## Post-Cleanup

After deleting `backend/`:

1. **Create new virtual environment** (if needed)
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Update .gitignore** (if needed)
   - Ensure `venv/`, `.env`, `__pycache__/` are ignored

3. **Update documentation**
   - Update README.md with new paths
   - Update any deployment scripts

## Rollback Plan

If something goes wrong:

1. Restore from backup:
   ```bash
   tar -xzf backend_backup_YYYYMMDD.tar.gz
   ```

2. Or restore from git:
   ```bash
   git checkout backend/
   ```

## Notes

- The old `backend/` folder is **completely replaced** by the new structure
- All code has been migrated to `apps/api/` and `packages/core/`
- Configuration files are now at root level
- The new structure matches `Project_Structure_GenAI.md` exactly

