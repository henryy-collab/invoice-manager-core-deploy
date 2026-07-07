# Deployment Guide for Coolify Cloud

This guide explains how to deploy Invoice Manager Core to Coolify Cloud using a pre-built Docker image from GitHub Container Registry (GHCR).

After the initial setup, every new release you tag in GitHub will automatically redeploy in Coolify.

---

## What you need before starting

- Access to the Coolify Cloud server.
- The service-account JSON key file (`connect-ai-pc-fad7ca673e19.json`).
- The `local/local_config.json` file with the correct settings.
- The `rclone.conf` file containing the `[mydrive-service]` remote.

---

## How releases work

1. The developer merges changes to the `master` branch.
2. The developer creates a Git tag, for example `v0.1.1`.
3. GitHub Actions builds a Docker image and pushes it to GHCR with two tags:
   - `ghcr.io/henryy-collab/invoice-manager-core:0.1.1`
   - `ghcr.io/henryy-collab/invoice-manager-core:latest`
4. Coolify Cloud detects the new `latest` image and redeploys automatically.

To roll back, change the image tag in Coolify from `latest` to a specific version such as `0.1.0`.

---

## Step 1: Create a GitHub personal access token

Coolify needs read access to the GHCR image.

1. Go to https://github.com/settings/tokens.
2. Click **Generate new token (classic)**.
3. Select the `read:packages` scope.
4. Generate and copy the token.

> Keep this token safe. You will paste it into Coolify.

---

## Step 2: Add the registry in Coolify Cloud

1. Open Coolify Cloud and go to **Settings → Registries**.
2. Click **Add Registry**.
3. Choose **GitHub Container Registry (GHCR)**.
4. Fill in:
   - **Username:** your GitHub username
   - **Password:** the personal access token from Step 1
5. Save.

---

## Step 3: Create the resource

1. In Coolify, click **Create New Resource**.
2. Choose **Docker Image**.
3. Select the GHCR registry you just added.
4. Enter the image:
   ```
   ghcr.io/henryy-collab/invoice-manager-core:latest
   ```
5. Click **Continue**.

---

## Step 4: Configure secrets

The container needs three files to function. You can provide them either as file mounts or as base64-encoded environment variables.

### Option A: File mounts (preferred)

1. In the resource settings, go to **Storage / Volumes**.
2. Add three file mounts:

   | Container path | Content |
   |---|---|
   | `/app/local/local_config.json` | Paste the full contents of `local/local_config.json` |
   | `/app/keys/connect-ai-pc-fad7ca673e19.json` | Paste the full contents of the service-account key |
   | `/root/.config/rclone/rclone.conf` | Paste the full contents of `rclone.conf` |

3. Add one persistent volume for runtime data:

   | Container path | Type |
   |---|---|
   | `/app/local/data` | Persistent volume |

### Option B: Base64 environment variables

If file mounts are not available, use the container's entrypoint to materialize the files from environment variables.

On your local machine, encode each file:

```bash
base64 -i local/local_config.json
base64 -i keys/connect-ai-pc-fad7ca673e19.json
base64 -i rclone.conf
```

In Coolify, add these environment variables:

| Name | Value |
|---|---|
| `APP_CONFIG_JSON_B64` | base64-encoded `local/local_config.json` |
| `SERVICE_ACCOUNT_JSON_B64` | base64-encoded service-account key |
| `RCLONE_CONF_B64` | base64-encoded `rclone.conf` |

Also add a persistent volume:

| Container path | Type |
|---|---|
| `/app/local/data` | Persistent volume |

---

## Step 5: Networking and health checks

1. Go to **Domains** and set the domain you want to use.
2. Go to **Healthcheck**.
3. Set the health-check URL to:
   ```
   /health
   ```
4. Leave the default port as `8000`.

---

## Step 6: Enable auto-deploy

1. In the resource settings, find **Auto Deploy** or **Webhooks**.
2. Enable auto-deploy for the image.

> Coolify will poll or receive a webhook when a new `latest` image is published.

---

## Step 7: Deploy

1. Click **Deploy** or **Start**.
2. Watch the deployment logs.
3. Open the domain in a browser to verify the UI loads.

---

## Troubleshooting

### Container fails to start

Check the deployment logs for:

- `WARNING: No app config mounted or provided via APP_CONFIG_JSON_B64` — the config file is missing.
- `WARNING: No rclone config mounted` — the rclone remote is missing.
- `WARNING: No service-account key mounted` — the Google key is missing.

### rclone commands fail

1. Verify `/root/.config/rclone/rclone.conf` contains `[mydrive-service]`.
2. Verify the service account has access to the Shared drive.
3. Run `rclone lsd mydrive-service:` from inside a shell in the running container.

### Health check fails

Make sure the health-check path is `/health` and the port is `8000`.

### Coolify does not redeploy on new releases

1. Confirm auto-deploy is enabled.
2. Check that Coolify is using the `latest` tag, not a pinned version.
3. Check the Coolify deployment logs for pull errors or registry authentication failures.

---

## Rollback

To roll back to a previous version:

1. In Coolify, change the image from:
   ```
   ghcr.io/henryy-collab/invoice-manager-core:latest
   ```
   to:
   ```
   ghcr.io/henryy-collab/invoice-manager-core:0.1.0
   ```
2. Redeploy.

---

## For developers: tagging a release

When the code is ready to deploy:

```bash
git checkout master
git pull
git tag v0.1.1
git push origin v0.1.1
```

GitHub Actions will build and publish the new image within a few minutes.
