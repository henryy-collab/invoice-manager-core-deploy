# Deployment Guide for Coolify

## Goal

Deploy Invoice Manager Core to Coolify using Docker Compose from the GitHub repository. After setup, every new Git tag can be selected in Coolify for a controlled version update.

## Prerequisites

- Access to a Coolify server.
- A GitHub repository the Coolify app can read (for example, `FirstPage-Glass/invoice-manager-core`).
- The service-account JSON key file named `connect-ai-pc-fad7ca673e19.json`.
- The app configuration file `local/local_config.json` with the current production settings.
- The rclone configuration file `rclone.conf` containing a remote named `[mydrive-service]`.

## How releases work

1. Changes are merged into `master` on the source-of-truth repo.
2. A maintainer pushes a Git tag, for example `v0.1.0`.
3. In Coolify, the resource source is changed from `master` to the tag `v0.1.0` and the resource is redeployed.
4. Coolify pulls the repository at that tag, builds the Docker image, and starts the container.

This gives full control over when each version is deployed.

## Step 1: Provide the secrets as environment variables (optional)

The container reads three files from environment variables. All are now **optional** — the app boots with the bundled example config (reachable UI, editable) even if none are set. Set them for full functionality.

| Variable | Value |
|---|---|
| `SERVICE_ACCOUNT_JSON` | The full contents of `connect-ai-pc-fad7ca673e19.json` (raw JSON, or base64-encoded via `SERVICE_ACCOUNT_JSON_B64`) |
| `APP_CONFIG_JSON` | The full contents of `local/local_config.json` as plain JSON |
| `RCLONE_CONF` | The full contents of `rclone.conf` with newlines replaced by `\|` pipe characters (or base64 via `RCLONE_CONF_B64`) |
| `NOCODB_TOKEN` | NocoDB API token (used by the `upload_nocodb.py` CLI, `xc-token` header) |
| `NOCODB_URL` | NocoDB base URL (default `http://localhost:3000`). For a deployed container use a URL reachable from the server, not `localhost`. |

The `RCLONE_CONF` pipe format is used because multi-line values are hard to paste into some deployment environments. For example:

```
[mydrive-service]\ntype = drive\nscope = drive\nservice_account_file = /app/keys/connect-ai-pc-fad7ca673e19.json
```

Secrets are materialized to disk at startup by `deploy/bootstrap.py`. If a variable is missing, the app logs a warning and continues instead of failing to boot.

## Step 2: Ensure the Coolify resource is configured

1. In Coolify, open the existing invoice-manager resource.
2. Confirm the source is a Docker Compose repository.
3. Confirm the source repository is the one Coolify can read (e.g., `FirstPage-Glass/invoice-manager-core`).
4. Confirm the branch is `master` for now.

## Step 3: Configure networking and health checks

1. Set the port to `8000`.
2. Set the health-check URL to `/health`.
3. Add a domain if you want a public URL.

## Step 4: Add persistent storage

Add one persistent volume:

| Container path | Type |
|---|---|
| `/app/local/data` | Persistent volume |

This keeps incoming PDFs, outgoing PDFs, logs, reports, and state across redeploys.

## Step 5: Deploy and verify

1. Click **Deploy** or **Start**.
2. Watch the deploy logs. With `APP_CONFIG_JSON` set you should see:
   - `Service-account key written from environment` (if `SERVICE_ACCOUNT_JSON` set)
   - `App config written from APP_CONFIG_JSON`
   - `Repairing config from env var...` (if the app config came from the env var)
   - `Config repaired successfully.`
3. Visit the domain or `/health` and confirm the response:
   ```json
   {"status": "ok"}
   ```
4. Test the preview workflow to confirm invoices parse correctly.

## Step 6: Roll out a new version

When the code is ready to release:

```bash
git checkout master
git pull
git tag v0.1.0
git push origin v0.1.0
```

Then sync the tag to the deployment repo if it differs from your source-of-truth repo.

In Coolify:

1. Open the resource.
2. Change the branch/tag from `master` to `v0.1.0`.
3. Redeploy.

## Rollback

To roll back to a previous version, change the tag in Coolify from the new tag back to the previous tag (e.g., `v0.1.0`) and redeploy.

## Common failures

### Container starts but warnings appear in logs

The app now boots even without secrets, so missing env vars produce warnings rather than a crash:

- `WARNING: No app config mounted or provided` — `APP_CONFIG_JSON` is missing. The app uses the bundled example config, which is functional for preview/rename but has Google Sheets and rclone disabled.
- `WARNING: No rclone config mounted or provided` — `RCLONE_CONF` is missing. rclone sync will be unavailable.
- `WARNING: No service-account key mounted or provided` — `SERVICE_ACCOUNT_JSON` is missing. Google Sheets reporting will be unavailable.

Set the corresponding env var and redeploy to enable the feature.

### Health check fails

- Confirm the port is `8000` and the path is `/health`.
- Confirm the container finished starting and is not in a crash loop. A crash loop now indicates a real bug (e.g. invalid `APP_CONFIG_JSON`), not a missing secret.

### Drive folder not found

The rclone error message now says `Drive folder not found or not accessible`. Check the `source_drive_folder` value in the config and confirm the folder still exists in Google Drive.
