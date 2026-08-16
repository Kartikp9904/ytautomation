# User Manual & Step-by-Step Tutorial

Welcome to the **YouTube Video Scheduling & Automation Platform**! This guide walks you through setting up channels, linking Google Drive folders, configuring automated scheduling rules, and monitoring uploads.

---

## 1. Connecting a YouTube Channel

1. Open the Web Dashboard (`http://localhost` or your server domain).
2. Navigate to **Channels** in the sidebar.
3. Click **"+ Add Channel"**.
4. Fill in the channel settings:
   - **Channel Name**: e.g., `Daily Coding Tips`.
   - **Timezone**: Select your target audience's timezone (e.g. `America/New_York`).
   - **Default Title Template**: e.g., `{channel} - Daily Tip #{day} ({month_name})`.
   - **Default Category**: e.g., `Science & Technology`.
   - **Privacy Status**: `private` (default for review) or `public`.
5. Click **"Save Channel"**.
6. On the Channel Card, click **"Connect YouTube"** to grant OAuth2 permissions for automated video uploads.

---

## 2. Ingesting Videos from Google Drive

1. Click **Google Drive** in the sidebar.
2. If not already authenticated, click **"Authenticate Google Drive"**.
3. Browse your Google Drive folder hierarchy.
4. Click **"Index Content Folder"** on your target video directory.
5. All `.mp4`, `.mov`, and `.mkv` files, along with sidecar `.json` metadata and `.jpg`/`.png` thumbnails, will be indexed into the **Library**.

---

## 3. Creating an Automation Schedule

1. Navigate to **Schedules** and click **"+ Create Schedule"**.
2. Select your channel and choose a **Scheduling Mode**:
   - **Day of Month (`DOM`)**: Selects videos by day index (`01_intro.mp4`, `15_review.mp4`).
   - **Rotation (`ROT`)**: Sequentially advances through videos in the folder and loops upon completion.
   - **Shuffle (`SHUF`)**: Non-repeating random cycle.
   - **Repeat (`REP`)**: Loops a single video across every scheduled time.
3. Configure the timing:
   - **Frequency**: `DAILY`, `WEEKDAYS`, or `WEEKLY`.
   - **Publish Time**: e.g., `18:00`.
   - **Lead Time Buffer**: e.g., `180 minutes` (uploads 3 hours early as private, then YouTube automatically publishes at the exact scheduled time via `publishAt`).
4. Click **"Save & Activate Schedule"**.

---

## 4. Calendar View & Dry-Run Simulation

1. Navigate to **Calendar** in the sidebar.
2. View all upcoming scheduled video releases on the 7-column monthly grid.
3. Use the **Dry-Run Simulator Panel** at the top:
   - Select any schedule and click **"Simulate Month"**.
   - Inspect video mappings, leap year fallbacks, and 30-day adjustments in real-time without modifying your live database or YouTube channel.

---

## 5. Live Uploads & Worker Logs

1. Navigate to **Upload Logs** in the sidebar.
2. Monitor real-time upload progress bars, retry counters, and video YouTube links.
3. If an upload fails due to temporary network issues, click **"Retry Upload"** or trigger **"Run Crash Reconciliation"**.
