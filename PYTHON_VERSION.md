# Python Version Requirement

## ⚠️ Important

The backend requires **Python 3.8 or higher** (ideally Python 3.11+).

Your current Python version is **3.7.3**, which is too old.

## Solutions

### Option 1: Install Python 3.11+ (Recommended)

**macOS (using Homebrew):**
```bash
brew install python@3.11
python3.11 -m venv venv
source venv/bin/activate
```

**Or use pyenv:**
```bash
brew install pyenv
pyenv install 3.11.7
pyenv local 3.11.7
python -m venv venv
source venv/bin/activate
```

### Option 2: Use Compatible Versions (Temporary)

I've updated `requirements.txt` to use versions compatible with Python 3.7, but this is **not recommended** for production. Some features may not work correctly.

### Option 3: Use Docker

The Dockerfile uses Python 3.11:
```bash
docker build -t scholarsync-backend ./backend
docker run -p 8000:8000 scholarsync-backend
```

## Verify Installation

After installing Python 3.11+:
```bash
python --version  # Should show 3.8+
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```


