# Deployment Guide for Coolify Cloud

## Goal

Deploy Invoice Manager Core to Coolify Cloud using the pre-built Docker image from GitHub Container Registry (GHCR). After setup, every new release tag pushed to GitHub will automatically redeploy in Coolify.

## Prerequisites

Confirm all of the following are available before starting:

- Access to a Coolify Cloud server.
- A GitHub account with access to `henryy-collab/invoice-manager-core`.
- The service-account JSON key file named `connect-ai-pc-fad7ca673e19.json`.
- The app configuration file `local/local_config.json` with the current production settings.
- The rclone configuration file `rclone.conf` containing a remote named `[mydrive-service]`.

## How releases work

1. The maintainer merges changes into the `master` branch.
2. The maintainer creates and pushes a Git tag, for example `v0.1.1`.
3. GitHub Actions builds a Docker image and pushes it to GHCR with two tags:
   - `ghcr.io/henryy-collab/invoice-manager-core:0.1.1`
   - `ghcr.io/henryy-collab/invoice-manager-core:latest`
4. Coolify Cloud detects the new `latest` image and redeploys automatically.

To roll back, change the image tag in Coolify from `latest` to a specific version such as `0.1.0`.

## Step 1: Create a GitHub personal access token

Coolify needs a token to read the GHCR image.

1. Open https://github.com/settings/tokens.
2. Click **Generate new token (classic)**.
3. Select the `read:packages` scope.
4. Generate the token and copy the value.
5. Store the token securely. It will be pasted into Coolify in the next step.

Expected result: a token string beginning with `ghp_` is saved in a password manager or secure note.

## Step 2: Add the GHCR registry to Coolify Cloud

1. Open Coolify Cloud and navigate to **Settings → Registries**.
2. Click **Add Registry**.
3. Choose **GitHub Container Registry (GHCR)**.
4. Enter the following values:
   - **Username:** your GitHub username
   - **Password:** the personal access token from Step 1
5. Save the registry.

Expected result: the registry appears in the list with a status of **Connected** or similar.

## Step 3: Create the Coolify resource

1. In Coolify, click **Create New Resource**.
2. Choose **Docker Image**.
3. Select the GHCR registry added in Step 2.
4. Enter the image URL:
   ```
   ghcr.io/henryy-collab/invoice-manager-core:latest
   ```
5. Click **Continue**.

Expected result: Coolify creates a new resource with the image configured.

## Step 4: Configure secrets

The container requires three files to function:

1. `/app/local/local_config.json` — app configuration
2. `/app/keys/connect-ai-pc-fad7ca673e19.json` — Google service-account key
3. `/root/.config/rclone/rclone.conf` — rclone remote configuration

Choose one method and follow it completely. Do not mix both methods.

### Method A: File mounts (preferred)

1. In the resource settings, go to **Storage / Volumes**.
2. Add three file mounts:

   | Container path | Content |
   |---|---|
   | `/app/local/local_config.json` | Paste the full contents of `local/local_config.json` |
   | `/app/keys/connect-ai-pc-fad7ca673e19.json` | Paste the full contents of `connect-ai-pc-fad7ca673e19.json` |
   | `/root/.config/rclone/rclone.conf` | Paste the full contents of `rclone.conf` |

3. Add one persistent volume for runtime data:

   | Container path | Type |
   |---|---|
   | `/app/local/data` | Persistent volume |

Expected result: the resource has three file mounts and one persistent volume listed.

### Method B: Base64 environment variables

Use this method only if file mounts are not available.

1. On a local machine, encode each file as base64:

   ```bash
   base64 -i local/local_config.json
   base64 -i keys/connect-ai-pc-fad7ca673e19.json
   base64 -i rclone.conf
   ```

2. In Coolify, add these environment variables:

   | Name | Value |
   |---|---|
   | `APP_CONFIG_JSON_B64` | base64-encoded contents of `local/local_config.json` |
   | `SERVICE_ACCOUNT_JSON_B64` | base64-encoded contents of `connect-ai-pc-fad7ca673e19.json` |
   | `RCLONE_CONF_B64` | base64-encoded contents of `rclone.conf` |

3. Add one persistent volume for runtime data:

   | Container path | Type |
   |---|---|
   | `/app/local/data` | Persistent volume |

Expected result: the resource has three environment variables and one persistent volume listed.

## Step 5: Configure networking and health checks

1. Go to **Domains** and set the domain for the application.
2. Go to **Healthcheck**.
3. Set the health-check URL to:
   ```
   /health
   ```
4. Leave the port as `8000`.

Expected result: the domain is saved and the health-check path is `/health` on port `8000`.

## Step 6: Enable auto-deploy

1. In the resource settings, locate **Auto Deploy** or **Webhooks**.
2. Enable auto-deploy for the image.

Expected result: auto-deploy is enabled and Coolify will pull new `latest` images when they are published.

## Step 7: Deploy and verify

1. Click **Deploy** or **Start**.
2. Wait for the deployment to finish.
3. Visit `https://<your-domain>/health` in a browser.

Expected result: the browser returns JSON:
```json
{"status": "ok"}
```

## Common failures

### Container fails to start

Check the deployment logs for one of these warnings:

- `WARNING: No app config mounted or provided via APP_CONFIG_JSON_B64` — the config file is missing.
- `WARNING: No rclone config mounted` — the rclone remote is missing.
- `WARNING: No service-account key mounted` — the Google key is missing.

### Health check fails

- Confirm the health-check URL is `/health` and the port is `8000`.
- Confirm the container has finished starting and is not in a crash loop.

### Coolify does not redeploy on new releases

1. Confirm auto-deploy is enabled.
2. Confirm the image tag is `latest`, not a pinned version.
3. Check the deployment logs for registry authentication errors.

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

## For the maintainer: tagging a release

When the code is ready to deploy:

```bash
git checkout master
git pull
git tag v0.1.1
git push origin v0.1.1
```

GitHub Actions will build and publish the new image within a few minutes.
