#!/usr/bin/env bash
# Example rclone script for Linux shared-PC setup.
# Edit BASE_DIR, REMOTE, and SOURCE_FOLDER to match your deployment.
set -euo pipefail

BASE_DIR="/var/invoice-manager"
REMOTE="mydrive-shared"
SOURCE_FOLDER="Auto Email Management/Google Ads/InvoicesRAW"

echo "Pulling raw invoices from Google Drive..."
rclone sync "${REMOTE}:${SOURCE_FOLDER}" "${BASE_DIR}/incoming"
echo "Pull complete. Files in ${BASE_DIR}/incoming"
