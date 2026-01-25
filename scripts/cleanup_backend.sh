#!/bin/bash
# Safe Backend Cleanup Script
# This script safely removes the old backend/ folder after preserving critical files

set -e  # Exit on error

echo "============================================================"
echo "Backend Cleanup Script"
echo "============================================================"
echo ""
echo "This script will:"
echo "  1. Preserve .env files from backend/"
echo "  2. Create a backup of backend/ folder"
echo "  3. Remove the old backend/ folder"
echo ""
read -p "Do you want to continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Cleanup cancelled."
    exit 0
fi

echo ""
echo "Step 1: Preserving .env files..."
echo "-----------------------------------"

# Preserve .env file
if [ -f "backend/.env" ] && [ ! -f ".env" ]; then
    echo "✓ Copying backend/.env to root..."
    cp backend/.env .env
    echo "  → .env preserved at root"
elif [ -f "backend/.env" ] && [ -f ".env" ]; then
    echo "⚠️  Both backend/.env and root .env exist"
    echo "  → Keeping root .env (backend/.env not copied)"
else
    echo "ℹ️  No backend/.env found (or already at root)"
fi

# Preserve .env.bak if needed
if [ -f "backend/.env.bak" ] && [ ! -f ".env.bak" ]; then
    echo "✓ Copying backend/.env.bak to root..."
    cp backend/.env.bak .env.bak
    echo "  → .env.bak preserved at root"
fi

echo ""
echo "Step 2: Creating backup..."
echo "-----------------------------------"
BACKUP_NAME="backend_backup_$(date +%Y%m%d_%H%M%S).tar.gz"
echo "Creating backup: $BACKUP_NAME"
tar -czf "$BACKUP_NAME" backend/ 2>/dev/null || {
    echo "⚠️  Could not create tar backup (continuing anyway)..."
}

if [ -f "$BACKUP_NAME" ]; then
    echo "✓ Backup created: $BACKUP_NAME"
    echo "  → Backup size: $(du -h "$BACKUP_NAME" | cut -f1)"
else
    echo "⚠️  Backup creation failed, but continuing..."
fi

echo ""
echo "Step 3: Removing old backend/ folder..."
echo "-----------------------------------"
echo "⚠️  This will permanently delete backend/ folder"
read -p "Are you absolutely sure? Type 'DELETE' to confirm: " delete_confirm

if [ "$delete_confirm" != "DELETE" ]; then
    echo "Cleanup cancelled. Backend folder preserved."
    exit 0
fi

# Move to trash (safer than rm -rf)
if command -v mv &> /dev/null; then
    TRASH_DIR="$HOME/.Trash"
    if [ -d "$TRASH_DIR" ]; then
        echo "Moving backend/ to Trash..."
        mv backend/ "$TRASH_DIR/backend_old_$(date +%Y%m%d_%H%M%S)" 2>/dev/null || {
            echo "⚠️  Could not move to Trash, using rm -rf instead..."
            rm -rf backend/
        }
    else
        echo "Trash not found, using rm -rf..."
        rm -rf backend/
    fi
else
    rm -rf backend/
fi

echo ""
echo "============================================================"
echo "✓ Cleanup Complete!"
echo "============================================================"
echo ""
echo "Summary:"
echo "  ✓ .env files preserved"
if [ -f "$BACKUP_NAME" ]; then
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

