#!/usr/bin/env bash
# Hermes Agent - Checkpoint Helper Script
set -e

MSG="${1:-auto-checkpoint}"
TIMESTAMP=$(date +"%Y-%m-%d_%H%M%S")
TAG_NAME="checkpoint-${TIMESTAMP}"

echo "=========================================="
echo "🔖 Creating Git Checkpoint..."
echo "=========================================="

git add .
git commit -m "checkpoint: ${MSG} (${TIMESTAMP})" || echo "No new changes to commit."
git tag -a "${TAG_NAME}" -m "${MSG}"

echo "✅ Checkpoint Created Successfully!"
echo "Tag Name: ${TAG_NAME}"
echo "To restore this checkpoint anytime, run:"
echo "  git checkout ${TAG_NAME}"
echo "=========================================="
