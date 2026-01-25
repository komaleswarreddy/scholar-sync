# Root Files Safety Audit

**Date**: 2025-01-25  
**Goal**: Identify files safe to move from root without breaking tooling

---

## Audit Results

### ❌ Files That MUST Stay at Root (Tool Auto-Discovery)

| File | Reason | Tool |
|------|--------|------|
| `package.json` | Monorepo root config | pnpm, Turborepo |
| `pnpm-lock.yaml` | Lock file for workspace | pnpm |
| `pnpm-workspace.yaml` | Workspace definition | pnpm |
| `turbo.json` | Turborepo config | Turborepo (auto-discovers at root) |
| `tsconfig.json` | TypeScript monorepo root config | TypeScript |
| `.prettierrc` | Prettier auto-discovers at root | Prettier |
| `.gitignore` | Git config (must be at root) | Git |
| `.dockerignore` | Docker auto-discovers at root | Docker |
| `alembic.ini` | Alembic auto-discovers at root | Alembic |
| `docker-compose.yml` | Standard location | docker-compose |
| `docker-compose.test.yml` | Standard location | docker-compose |
| `Makefile` | Standard location | make |
| `README.md` | Convention (repo entry point) | - |
| `.env.example` | Convention | - |

### ⚠️ Files That Could Move But Risky (Many References)

| File | Current References | Risk Level | Decision |
|------|-------------------|------------|----------|
| `requirements.txt` | Dockerfile.api, Dockerfile.worker, Makefile, scripts | HIGH | ❌ KEEP |
| `Dockerfile.api` | docker-compose.yml, docker-compose.test.yml | MEDIUM | ❌ KEEP |
| `Dockerfile.worker` | docker-compose.yml | MEDIUM | ❌ KEEP |
| `pyproject.toml` | Standard Python location | LOW | ❌ KEEP (standard) |

### ✅ Files Safe to Move/Remove

| File | Current Location | Target | Reason |
|------|-----------------|--------|--------|
| `backend_backup_*.tar.gz` | Root | `docs/dev/` or delete | Backup file, not needed in repo |

---

## Analysis Details

### .prettierrc Analysis

**Current State:**
- Prettier auto-discovers `.prettierrc` at root
- No explicit config path in package.json
- No references in scripts

**Safety Check:**
- ✅ Can add to package.json: `"prettier": ".prettierrc"` or `"prettier": "config/.prettierrc"`
- ⚠️ But Prettier auto-discovery is standard and expected at root
- ⚠️ Moving would require updating all tooling/configs

**Decision**: ❌ **KEEP at root** - Standard convention, low benefit from moving

### requirements.txt Analysis

**Current References:**
- `Dockerfile.api`: `COPY requirements.txt .`
- `Dockerfile.worker`: `COPY requirements.txt .`
- `Makefile`: `pip install -r requirements.txt`
- Scripts: Referenced in cleanup scripts

**Safety Check:**
- ⚠️ Would need to update 4+ files
- ⚠️ Dockerfiles expect it at root (standard)
- ⚠️ Risk of breaking Docker builds

**Decision**: ❌ **KEEP at root** - Too many references, standard location

### Dockerfile.* Analysis

**Current References:**
- `docker-compose.yml`: `dockerfile: Dockerfile.api`
- `docker-compose.test.yml`: `dockerfile: Dockerfile.api`

**Safety Check:**
- ⚠️ Would need to update docker-compose files
- ⚠️ Standard location is root
- ⚠️ Risk of breaking docker-compose

**Decision**: ❌ **KEEP at root** - Standard location, references in compose files

---

## Final Decision

### Files to Move: 0

**All root files are either:**
1. Required by tools at root (auto-discovery)
2. Standard convention (README, .env.example)
3. Too risky to move (many references)

### Files to Remove/Archive: 1

- `backend_backup_*.tar.gz` → Can be moved to `docs/dev/` or deleted (backup file)

---

## Recommendation

**Keep all root files as-is.**

The root is appropriately organized with:
- Standard tool configs (package.json, turbo.json, tsconfig.json)
- Standard conventions (README.md, .env.example)
- Docker/infrastructure files (standard location)
- Python configs (standard location)

**Only action**: Remove or archive `backend_backup_*.tar.gz` (backup file, not needed in repo)

