#!/bin/bash
# Comprehensive Import Verification Script

echo "============================================================"
echo "Comprehensive Import Verification"
echo "============================================================"
echo ""

echo "1. Syntax Check..."
python3 scripts/check_import_syntax.py
echo ""

echo "2. Circular Dependency Check..."
python3 scripts/check_circular_deps.py
echo ""

echo "============================================================"
echo "Verification Complete"
echo "============================================================"

