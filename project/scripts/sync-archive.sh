#!/usr/bin/env bash
# Example rclone script for Linux shared-PC setup.
# Edit BASE_DIR, REMOTE, and ARCHIVE_FOLDER to match your deployment.
set -euo pipefail

BASE_DIR="/var/invoice-manager"
REMOTE="mydrive-shared"
ARCHIVE_FOLDER="Auto Email Management/Google Ads/Invoices/archive"

echo "Pushing archive to Google Drive..."
rclone copy "${BASE_DIR}/archive" "${REMOTE}:${ARCHIVE_FOLDER}"
echo "Archive push complete. Files synced to ${REMOTE}:${ARCHIVE_FOLDER}"
