#!/bin/bash
set -e

KEY_FILE="/app/keys/connect-ai-pc-fad7ca673e19.json"
CONFIG_FILE="/app/local/local_config.json"
RCLONE_FILE="/root/.config/rclone/rclone.conf"

write_from_b64() {
    local dest="$1"
    local b64_value="$2"
    mkdir -p "$(dirname "$dest")"
    echo "$b64_value" | base64 -d > "$dest"
}

config_from_env=false

if [ -f "$KEY_FILE" ]; then
    echo "Service-account key already mounted at $KEY_FILE"
elif [ -n "$SERVICE_ACCOUNT_JSON_B64" ]; then
    write_from_b64 "$KEY_FILE" "$SERVICE_ACCOUNT_JSON_B64"
    chmod 600 "$KEY_FILE"
    echo "Service-account key written from SERVICE_ACCOUNT_JSON_B64"
elif [ -n "$SERVICE_ACCOUNT_JSON" ]; then
    mkdir -p "$(dirname "$KEY_FILE")"
    echo "$SERVICE_ACCOUNT_JSON" | base64 -d > "$KEY_FILE"
    chmod 600 "$KEY_FILE"
    echo "Service-account key written from SERVICE_ACCOUNT_JSON"
else
    echo "WARNING: No service-account key mounted or provided"
fi

if [ -f "$CONFIG_FILE" ]; then
    echo "App config already mounted at $CONFIG_FILE"
elif [ -n "$APP_CONFIG_JSON_B64" ]; then
    write_from_b64 "$CONFIG_FILE" "$APP_CONFIG_JSON_B64"
    config_from_env=true
    echo "App config written from APP_CONFIG_JSON_B64"
elif [ -n "$APP_CONFIG_JSON" ]; then
    mkdir -p "$(dirname "$CONFIG_FILE")"
    echo "$APP_CONFIG_JSON" > "$CONFIG_FILE"
    config_from_env=true
    echo "App config written from APP_CONFIG_JSON"
else
    echo "WARNING: No app config mounted or provided"
fi

if [ "$config_from_env" = true ]; then
    echo "Repairing config from env var..."
    python /repair_config.py || echo "Warning: config repair failed"
fi

if [ -f "$RCLONE_FILE" ]; then
    echo "rclone config already mounted at $RCLONE_FILE"
elif [ -n "$RCLONE_CONF_B64" ]; then
    mkdir -p /root/.config/rclone
    write_from_b64 "$RCLONE_FILE" "$RCLONE_CONF_B64"
    chmod 600 "$RCLONE_FILE"
    echo "rclone config written from RCLONE_CONF_B64"
elif [ -n "$RCLONE_CONF" ]; then
    mkdir -p /root/.config/rclone
    echo "$RCLONE_CONF" | tr '|' '\n' > "$RCLONE_FILE"
    chmod 600 "$RCLONE_FILE"
    echo "rclone config written from RCLONE_CONF"
else
    echo "WARNING: No rclone config mounted or provided"
fi

exec "$@"
