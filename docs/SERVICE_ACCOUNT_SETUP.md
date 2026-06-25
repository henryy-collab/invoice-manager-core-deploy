# Service Account Setup for Google Shared Drive

This guide configures Invoice Manager on a shared PC to access an existing Google Workspace Shared drive using a Google service account, instead of authenticating rclone with a personal Google account.

---

## Why use a service account

- The shared PC does not store a personal Google OAuth token.
- Access is scoped to a single JSON key that can be restricted, rotated, and audited.
- The Google Apps Script downloader in `v2/` does not need to change.

---

## Prerequisites

- A Google Workspace Shared drive that already contains (or will contain) the `InvoicesRAW` and `Invoices` folders.
- Permission to add external accounts to that Shared drive. Your Workspace admin may need to allow this in **Apps > Google Workspace > Drive and Docs > Sharing settings**.
- A Google Cloud project. The service account can be created under the same Workspace organization or a separate one. It will still be labelled as "external" when sharing in Drive. This is normal.

---

## 1. Create a service account

1. Open [Google Cloud Console](https://console.cloud.google.com/).
2. Go to **IAM & Admin > Service accounts**.
3. Click **Create service account**.
4. Give it a name such as `invoice-manager-shared-drive`.
5. Skip the optional grants for now.
6. Finish creating the account.

---

## 2. Enable Google APIs

1. In the same Cloud project, go to **APIs & Services > Enabled APIs & services**.
2. Click **Enable APIs and services**.
3. Search for **Google Drive API** and enable it.
4. Search for **Google Sheets API** and enable it.

---

## 3. Create and download a JSON key

1. Go to **IAM & Admin > Service accounts**.
2. Click the service account you created.
3. Select the **Keys** tab, then **Add Key > Create new key**.
4. Choose **JSON** and download the file.
5. Move the JSON file to the shared PC in a restricted location, for example:

   ```bash
   /opt/invoice-manager/.secrets/service-account.json
   ```

6. Set restrictive permissions so only the user running invoice-manager can read it:

   ```bash
   chmod 600 /opt/invoice-manager/.secrets/service-account.json
   ```

---

## 4. Add the service account to the Shared drive

1. In Google Drive, click the **Shared drive name** (not a folder inside it).
2. Click **Share** and add the service-account email address. It looks like:

   ```
   invoice-manager-shared-drive@<project-id>.iam.gserviceaccount.com
   ```

3. Assign the **Content manager** role. This is the highest role normally available for service accounts labelled external, and it is sufficient for this workflow.
4. Confirm the share succeeds.

The service account must be a member of the Shared drive itself. Sharing only a folder inside the Shared drive is not enough for rclone to discover the drive.

---

## 5. Find the Shared drive ID

1. Open the Shared drive in Google Drive.
2. The URL will be similar to:

   ```
   https://drive.google.com/drive/u/0/folders/<SHARED_DRIVE_ID>
   ```

3. Copy the `SHARED_DRIVE_ID` value.

---

## 6. Configure rclone

Run:

```bash
rclone config
```

If you already have a `mydrive-shared` remote using OAuth, edit it. Otherwise create a new one:

```bash
n              # new remote
mydrive-shared # name
```

When prompted:

- **Storage**: `drive`
- **Google Application Client Id**: leave blank and press Enter
- **Google Application Client Secret**: leave blank and press Enter
- **Scope**: `drive`
- **Service Account File**: path to the JSON key, e.g. `/opt/invoice-manager/.secrets/service-account.json`
- **Edit advanced config**: `n`
- **Configure this as a Shared Drive**: `y`
- **Shared Drive ID**: paste the ID from step 5

Confirm with `y`.

### Switching from OAuth

If the `mydrive-shared` remote previously used OAuth, remove the old token so the personal account is no longer stored on the shared PC:

```bash
rclone config show mydrive-shared
```

Look for a `token = {...}` line. The token file path is usually shown in the same output. Delete that file, then run `rclone config` again and switch to `service_account_file`.

---

## 7. Verify access

List the Shared drive:

```bash
rclone lsd mydrive-shared:
```

List the raw invoice folder:

```bash
rclone ls mydrive-shared:"Auto Email Management/Google Ads/InvoicesRAW"
```

Test write access safely by creating and deleting a temporary file:

```bash
echo "test" > /tmp/rclone-test.txt
rclone copy /tmp/rclone-test.txt mydrive-shared:"Auto Email Management/Google Ads/Invoices/"
rclone ls mydrive-shared:"Auto Email Management/Google Ads/Invoices/"
rclone delete mydrive-shared:"Auto Email Management/Google Ads/Invoices/rclone-test.txt"
```

If all commands succeed, the service account is correctly configured.

---

## 8. Configure Invoice Manager

Set `rclone.enabled` to `true` in `local/local_config.json` and confirm the remote name matches the one you created:

```json
{
  "rclone": {
    "enabled": true,
    "remote": "mydrive-shared",
    "source_drive_folder": "Auto Email Management/Google Ads/InvoicesRAW",
    "destination_drive_folder": "Auto Email Management/Google Ads/Invoices",
    "archive_drive_folder": null
  }
}
```

If you are using the Google Sheets report, add the `google_sheets` section and reuse the same service-account key:

```json
{
  "google_sheets": {
    "enabled": true,
    "spreadsheet_url": "https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit",
    "service_account_file": "/opt/invoice-manager/.secrets/service-account.json",
    "tab_name_template": "%b %Y",
    "date_format": "%d/%m/%Y",
    "skip_existing_by": "number",
    "raw_sheet_suffix": " [Auto]",
    "protect_raw_sheets": true
  }
}
```

Relative paths for `service_account_file` are resolved from the project root. For example, if the key is at `keys/service-account.json` next to the `local/` and `ui/` folders, use `"service_account_file": "keys/service-account.json"`.

The service account must have **Editor** access to the spreadsheet. The easiest way is to share the spreadsheet directly with the service-account email address, or place the spreadsheet inside a Shared drive folder where the service account already has **Content manager** or higher access.

The app never accesses Google Drive directly. rclone handles all sync operations; Google Sheets writes use the same service-account credentials.

---

## Notes

- The Google Apps Script downloader in `v2/` continues to run as whatever account it currently uses. It only needs access to the same Shared drive `InvoicesRAW` folder.
- Service accounts do not have Gmail, so they cannot receive share invitations. Add them directly to the Shared drive as described in step 4.
- If rclone reports `no shared drives found`, the service account has not been added to the Shared drive itself, or the Workspace admin has disabled external sharing.
