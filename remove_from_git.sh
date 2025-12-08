#!/bin/bash
# Script to remove large folders from git tracking while keeping them locally

echo "Removing large folders from git tracking..."
git rm -r --cached output/ 2>/dev/null || true
git rm -r --cached video_inputs/ 2>/dev/null || true
git rm -r --cached voice_inputs/ 2>/dev/null || true
git rm -r --cached references/ 2>/dev/null || true
git rm -r --cached scripts/ 2>/dev/null || true

echo "Done! These folders are now removed from git tracking."
echo "They will still exist locally but won't be included in deployments."
echo ""
echo "Next steps:"
echo "1. Commit this change: git commit -m 'Remove large data folders from git tracking'"
echo "2. Push to your repository"
echo "3. Redeploy on Vercel"

