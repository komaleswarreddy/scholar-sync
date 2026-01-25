# Missing Files Analysis Report

**Date**: 2025-01-25  
**Scope**: Analysis of missing infrastructure/config files

---

## Files Status

### ✅ Existing Files

1. **Dockerfile.api** ✅ EXISTS
   - Location: Root
   - Status: Created during cleanup
   - Purpose: Docker image for FastAPI API server
   - Content: Uses `apps.api.main:app` (correct for new structure)

2. **alembic.ini** ✅ EXISTS
   - Location: Root
   - Status: Created during cleanup
   - Purpose: Alembic database migration configuration
   - Content: Points to `packages/core/database/migrations` (correct)

### ❌ Missing Files

1. **.dockerignore** ❌ MISSING
   - **Needed**: YES
   - **Purpose**: Exclude files from Docker build context
   - **Should contain**: node_modules, venv, __pycache__, .env, .git, etc.
   - **Impact**: Without this, Docker builds will be slow and include unnecessary files

2. **Dockerfile.worker** ❌ MISSING
   - **Needed**: YES (if using Celery worker)
   - **Purpose**: Docker image for Celery worker
   - **Should contain**: Similar to Dockerfile.api but runs Celery instead
   - **Impact**: Cannot containerize worker without this

3. **docker-compose.yml** ❌ MISSING
   - **Needed**: YES (for local development)
   - **Purpose**: Orchestrate API + Worker + Database + Redis
   - **Should contain**: Services for api, worker, postgres, redis
   - **Impact**: Harder to run full stack locally without this

4. **docker-compose.test.yml** ❌ MISSING
   - **Needed**: OPTIONAL (but recommended)
   - **Purpose**: Test environment with isolated services
   - **Should contain**: Test database, test services
   - **Impact**: Testing is harder without isolated test environment

5. **pyproject.toml** ❌ MISSING
   - **Needed**: YES (for Python package management)
   - **Purpose**: 
     - Define Python package structure
     - Manage dependencies for `packages/core/`
     - Enable editable installs for development
   - **Should contain**: 
     - Package metadata
     - Dependencies
     - Build configuration
   - **Impact**: Cannot properly manage `packages/core/` as a Python package

6. **Makefile** ❌ MISSING
   - **Needed**: OPTIONAL (but recommended)
   - **Purpose**: Common development tasks (setup, test, run, etc.)
   - **Should contain**: 
     - `make setup` - Install dependencies
     - `make dev` - Start dev servers
     - `make test` - Run tests
     - `make migrate` - Run migrations
   - **Impact**: Developers need to remember long commands instead of `make dev`

---

## Analysis by File

### 1. .dockerignore

**Status**: ❌ MISSING  
**Priority**: HIGH  
**Needed**: YES

**What it should contain:**
```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
.venv/
env/
ENV/
*.egg-info/
.pytest_cache/
.coverage
htmlcov/

# Node
node_modules/
.npm
.pnp
.pnp.js

# Environment
.env
.env.local
.env.*.local
.env.bak

# IDE
.vscode/
.idea/
*.swp
*.swo

# Git
.git/
.gitignore

# Docs (not needed in container)
docs/
*.md

# Tests (not needed in container)
tests/
evals/

# Infrastructure (not needed in container)
infrastructure/

# Build artifacts
dist/
build/
.turbo

# OS
.DS_Store
Thumbs.db

# Backups
*.tar.gz
backend_backup_*
```

**Why needed**: Without this, Docker builds will:
- Include node_modules (huge, unnecessary)
- Include venv (huge, unnecessary)
- Include .git (unnecessary)
- Include docs and tests (unnecessary in production)
- Be slow and create large images

---

### 2. Dockerfile.worker

**Status**: ❌ MISSING  
**Priority**: HIGH (if using Celery)  
**Needed**: YES

**What it should contain:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Celery
RUN pip install --no-cache-dir celery[redis]

# Copy application code
COPY . .

# Run Celery worker
CMD ["celery", "-A", "apps.worker.celery_app", "worker", "--loglevel=info"]
```

**Why needed**: 
- Worker needs separate container from API
- Different entry point (Celery vs uvicorn)
- Can scale independently

**Current state**: `apps/worker/celery_app.py` exists but is placeholder

---

### 3. docker-compose.yml

**Status**: ❌ MISSING  
**Priority**: HIGH  
**Needed**: YES

**What it should contain:**
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: scholarsync
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  api:
    build:
      context: .
      dockerfile: Dockerfile.api
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/scholarsync
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis
    volumes:
      - .:/app
    command: uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload

  worker:
    build:
      context: .
      dockerfile: Dockerfile.worker
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/scholarsync
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis
    volumes:
      - .:/app
    command: celery -A apps.worker.celery_app worker --loglevel=info

volumes:
  postgres_data:
```

**Why needed**:
- Easy local development setup
- Run entire stack with one command: `docker-compose up`
- Consistent environment across developers
- Includes database and Redis

---

### 4. docker-compose.test.yml

**Status**: ❌ MISSING  
**Priority**: MEDIUM  
**Needed**: OPTIONAL (but recommended)

**What it should contain:**
- Similar to docker-compose.yml but:
  - Separate test database
  - Test-specific environment variables
  - Services for running tests

**Why needed**:
- Isolated test environment
- No interference with dev database
- CI/CD integration

**Impact**: Tests can run against dev database (acceptable but not ideal)

---

### 5. pyproject.toml

**Status**: ❌ MISSING  
**Priority**: HIGH  
**Needed**: YES

**What it should contain:**
```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "scholarsync-core"
version = "0.1.0"
description = "ScholarSync core packages"
requires-python = ">=3.11"
dependencies = [
    # List dependencies from requirements.txt
]

[project.optional-dependencies]
dev = [
    "pytest",
    "pytest-asyncio",
    "black",
    "ruff",
]

[tool.setuptools.packages.find]
where = ["packages/core"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
```

**Why needed**:
- `packages/core/` is a Python package
- Enables `pip install -e packages/core/` for development
- Proper dependency management
- Project structure shows `packages/core/pyproject.toml` should exist

**Current state**: Structure shows it should exist but it's missing

---

### 6. Makefile

**Status**: ❌ MISSING  
**Priority**: MEDIUM  
**Needed**: OPTIONAL (but recommended)

**What it should contain:**
```makefile
.PHONY: setup dev test migrate clean

setup:
	pip install -r requirements.txt
	pip install -e packages/core/
	pnpm install

dev:
	docker-compose up

test:
	pytest tests/

migrate:
	alembic upgrade head

clean:
	find . -type d -name __pycache__ -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
```

**Why needed**:
- Standardize common tasks
- Easier onboarding for new developers
- Consistent commands across team

**Impact**: Developers use long commands (acceptable but less convenient)

---

## Summary

### Critical (Must Have)

1. **.dockerignore** - HIGH priority
   - Needed for efficient Docker builds
   - Prevents including unnecessary files

2. **Dockerfile.worker** - HIGH priority (if using Celery)
   - Needed to containerize worker
   - Current worker is placeholder, but structure expects it

3. **docker-compose.yml** - HIGH priority
   - Needed for local development
   - Makes running full stack easy

4. **pyproject.toml** - HIGH priority
   - Needed for `packages/core/` package management
   - Structure document shows it should exist

### Recommended (Should Have)

5. **docker-compose.test.yml** - MEDIUM priority
   - Better test isolation
   - But tests can work without it

6. **Makefile** - MEDIUM priority
   - Developer convenience
   - But not required for functionality

---

## Recommendations

### Immediate Actions

1. **Create .dockerignore** - Prevents slow Docker builds
2. **Create pyproject.toml** - Required for package structure
3. **Create docker-compose.yml** - Essential for local dev

### When Worker is Implemented

4. **Create Dockerfile.worker** - When Celery worker is fully implemented

### Nice to Have

5. **Create Makefile** - Developer convenience
6. **Create docker-compose.test.yml** - Better test isolation

---

## Current State vs Target Structure

**Project_Structure_GenAI.md shows:**
- ✅ `Dockerfile.api` - EXISTS
- ✅ `Dockerfile.worker` - Should exist (missing)
- ✅ `docker-compose.yml` - Should exist (missing)
- ✅ `docker-compose.test.yml` - Should exist (missing)
- ✅ `pyproject.toml` - Should exist (missing)
- ✅ `alembic.ini` - EXISTS
- ✅ `Makefile` - Should exist (missing)
- ❌ `.dockerignore` - Not shown but needed

**Gap**: 5 files missing, 1 additional file needed (.dockerignore)

---

## Conclusion

**Missing files that need code/data:**
- `.dockerignore` - Needs ignore patterns
- `Dockerfile.worker` - Needs Dockerfile content (when worker implemented)
- `docker-compose.yml` - Needs service definitions
- `docker-compose.test.yml` - Needs test service definitions (optional)
- `pyproject.toml` - Needs package configuration
- `Makefile` - Needs make targets (optional)

**All missing files have clear purposes and should be created when ready.**

