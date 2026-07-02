#!/usr/bin/env bash
# Example rclone script for Linux shared-PC setup.
# Edit BASE_DIR, REMOTE, and DEST_FOLDER to match your deployment.
set -euo pipefail

BASE_DIR="/var/invoice-manager"
REMOTE="mydrive-shared"
DEST_FOLDER="Auto Email Management/Google Ads/Invoices"

echo "Pushing processed invoices to Google Drive..."
rclone copy "${BASE_DIR}/outgoing" "${REMOTE}:${DEST_FOLDER}"
echo "Push complete. Files synced to ${REMOTE}:${DEST_FOLDER}"
