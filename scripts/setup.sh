#!/bin/bash
# Setup script for AutoDev Agent

set -e

echo "Setting up AutoDev Agent..."

# Check for required tools
command -v python3 >/dev/null 2>&1 || { echo "Python 3 is required"; exit 1; }
command -v gh >/dev/null 2>&1 || { echo "GitHub CLI is required"; exit 1; }

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -e ".[dev]"

# Verify GitHub authentication
echo "Verifying GitHub authentication..."
gh auth status || { echo "Please run 'gh auth login' first"; exit 1; }

# Create data directories
mkdir -p data repos

echo ""
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Set ANTHROPIC_API_KEY environment variable"
echo "2. Run 'python -m autodev.main discover --dry-run' to test"
echo "3. Create tracking issues in target repositories"
echo ""
