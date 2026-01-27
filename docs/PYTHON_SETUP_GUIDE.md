# Python Environment Setup Guide

## Issue

Your system has Python 3.7.3, but this project requires **Python 3.8+** (recommended: Python 3.11+).

FastAPI 0.109.0 and other dependencies require Python 3.8 or higher.

---

## Solution Options

### Option 1: Install Python 3.11 via Homebrew (Recommended for macOS)

```bash
# Install Homebrew if you don't have it
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python 3.11
brew install python@3.11

# Verify installation
python3.11 --version

# Create virtual environment with Python 3.11
python3.11 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Start backend
uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload
```

---

### Option 2: Use Docker (Easiest - No Python Installation Needed)

```bash
# Start backend using Docker
docker-compose up api

# Or start all services
docker-compose up
```

This will:
- Use Python 3.11 from the Docker image
- Automatically install dependencies
- Start the API server on port 8000

---

### Option 3: Use pyenv (Python Version Manager)

```bash
# Install pyenv
brew install pyenv

# Install Python 3.11
pyenv install 3.11.7

# Set local Python version for this project
pyenv local 3.11.7

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Start backend
uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload
```

---

### Option 4: Download Python from python.org

1. Go to https://www.python.org/downloads/
2. Download Python 3.11+ for macOS
3. Install it
4. Use the new Python to create venv:
   ```bash
   /usr/local/bin/python3.11 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

---

## Quick Start (After Python 3.11 is Installed)

```bash
# 1. Create virtual environment
python3.11 -m venv venv

# 2. Activate it
source venv/bin/activate

# 3. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Start backend
uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## Verify Installation

After setup, verify everything works:

```bash
# Check Python version
python --version  # Should show 3.8+

# Check FastAPI
python -c "import fastapi; print(fastapi.__version__)"

# Test backend
curl http://localhost:8000/api/v1/health
```

---

## Current Status

- ✅ Frontend: Running on http://localhost:3000
- ❌ Backend: Not running (Python version issue)

Once Python 3.11 is installed and dependencies are installed, the backend will start successfully.

