#!/bin/bash
# Automated Backend Cleanup Script
# This script removes the old backend/ folder after preserving critical files
# Use this if you want to skip interactive prompts

set -e  # Exit on error

echo "============================================================"
echo "Automated Backend Cleanup Script"
echo "============================================================"
echo ""

# Step 1: Preserve .env files
echo "Step 1: Preserving .env files..."
echo "-----------------------------------"

if [ -f "backend/.env" ] && [ ! -f ".env" ]; then
    echo "✓ Copying backend/.env to root..."
    cp backend/.env .env
    echo "  → .env preserved at root"
elif [ -f "backend/.env" ] && [ -f ".env" ]; then
    echo "ℹ️  Root .env already exists, keeping it"
else
    echo "ℹ️  No backend/.env found"
fi

if [ -f "backend/.env.bak" ] && [ ! -f ".env.bak" ]; then
    echo "✓ Copying backend/.env.bak to root..."
    cp backend/.env.bak .env.bak
    echo "  → .env.bak preserved at root"
fi

# Step 2: Create backup
echo ""
echo "Step 2: Creating backup..."
echo "-----------------------------------"
BACKUP_NAME="backend_backup_$(date +%Y%m%d_%H%M%S).tar.gz"
echo "Creating backup: $BACKUP_NAME"

if tar -czf "$BACKUP_NAME" backend/ 2>/dev/null; then
    echo "✓ Backup created: $BACKUP_NAME"
    BACKUP_SIZE=$(du -h "$BACKUP_NAME" 2>/dev/null | cut -f1)
    echo "  → Backup size: $BACKUP_SIZE"
else
    echo "⚠️  Could not create tar backup (continuing anyway)..."
    BACKUP_NAME=""
fi

# Step 3: Remove backend folder
echo ""
echo "Step 3: Removing old backend/ folder..."
echo "-----------------------------------"

# Move to trash (safer than rm -rf)
TRASH_DIR="$HOME/.Trash"
if [ -d "$TRASH_DIR" ] && [ -d "backend" ]; then
    TRASH_NAME="$TRASH_DIR/backend_old_$(date +%Y%m%d_%H%M%S)"
    echo "Moving backend/ to Trash: $TRASH_NAME"
    if mv backend/ "$TRASH_NAME" 2>/dev/null; then
        echo "✓ backend/ moved to Trash"
    else
        echo "⚠️  Could not move to Trash, using rm -rf..."
        rm -rf backend/
        echo "✓ backend/ removed"
    fi
elif [ -d "backend" ]; then
    echo "Trash not found, using rm -rf..."
    rm -rf backend/
    echo "✓ backend/ removed"
else
    echo "ℹ️  backend/ folder not found (already removed?)"
fi

echo ""
echo "============================================================"
echo "✓ Cleanup Complete!"
echo "============================================================"
echo ""
echo "Summary:"
if [ -f ".env" ]; then
    echo "  ✓ .env file preserved at root"
fi
if [ -n "$BACKUP_NAME" ] && [ -f "$BACKUP_NAME" ]; then
    echo "  ✓ Backup created: $BACKUP_NAME"
fi
echo "  ✓ backend/ folder removed"
echo ""
echo "Next steps:"
echo "  1. Create new virtual environment: python -m venv venv"
echo "  2. Activate: source venv/bin/activate"
echo "  3. Install dependencies: pip install -r requirements.txt"
echo "  4. Test: python -m uvicorn apps.api.main:app --help"
echo ""

