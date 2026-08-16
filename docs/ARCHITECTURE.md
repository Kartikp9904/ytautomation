# System Architecture & Technical Specifications

This document outlines the software architecture, data flow, security model, and concurrency mechanics of the self-hosted **YouTube Video Scheduling & Automation Platform**.

---

## 1. High-Level Architecture Diagram

```
+-------------------------------------------------------------------------------+
|                             Client Layer (Browser)                            |
|  React 18 + TypeScript + Vite + Tailwind CSS + Lucide Icons (SPA Dashboard)   |
+---------------------------------------+---------------------------------------+
                                        | HTTPS / REST / JSON
                                        v
+-------------------------------------------------------------------------------+
|                      Host Reverse Proxy & Edge Security                       |
|  Nginx + Certbot TLS 1.3 + Rate Limiting (5r/m auth) + Fail2ban + UFW         |
+---------------------------------------+---------------------------------------+
                                        | Reverse Proxy (Port 8000)
                                        v
+-------------------------------------------------------------------------------+
|                         FastAPI Application Backend                           |
|                                                                               |
|  +---------------------+  +----------------------+  +----------------------+  |
|  |   API Endpoints     |  |   Metadata Engine    |  |  APScheduler Engine  |  |
|  | Channels, Videos,   |  | 5-Tier Priority Rule |  | Multi-Frequency &    |  |
|  | Schedules, Uploads  |  | Template Substituter |  | Timezone Precision   |  |
|  +----------+----------+  +----------+-----------+  +----------+-----------+  |
|             |                        |                         |              |
|             v                        v                         v              |
|  +-------------------------------------------------------------------------+  |
|  |                     UploadWorkerPool & Concurrency                      |  |
|  | Global Max Slots (3), Per-Channel Lock, 5s Anti-Burst Cooldown Delay    |  |
|  +-----------------------------------+-------------------------------------+  |
|                                      |                                        |
|                                      v                                        |
|  +-------------------------------------------------------------------------+  |
|  |                ReconciliationService & Error Classifier                 |  |
|  | Exponential Backoff + Jitter, Idempotency Checks, Orphan File Cleanup   |  |
|  +-----------------------------------+-------------------------------------+  |
+--------------------------------------+----------------------------------------+
                                       |
                   +-------------------+-------------------+
                   |                                       |
                   v                                       v
+--------------------------------------+ +--------------------------------------+
|           Data Persistence           | |           External APIs              |
| SQLite 3 (WAL Mode) / PostgreSQL 16  | | - Google Drive API v3 (Scanner/Chunk)|
| AES-256 Fernet Encrypted OAuth Tokens| | - YouTube Data API v3 (Resumable)    |
+--------------------------------------+ +--------------------------------------+
```

---

## 2. Core Subsystems

### 2.1 Metadata Hierarchy Resolution Engine (`MetadataEngine`)
The platform resolves video titles, descriptions, tags, and category IDs using a **5-tier priority hierarchy**:
1. **Tier 1 (Highest)**: Sidecar metadata file (`{videoname}.json`).
2. **Tier 2**: Folder-level custom metadata template.
3. **Tier 3**: Channel-level default metadata template.
4. **Tier 4**: Auto-extracted numeric Day-of-Month index.
5. **Tier 5 (Lowest)**: Raw sanitized video filename.

#### Dynamic Template Variable Substitutions:
- `{channel}` $\rightarrow$ Channel display name.
- `{title}` $\rightarrow$ Cleaned video base name.
- `{day}` $\rightarrow$ Two-digit numeric day index (e.g. `01`, `15`).
- `{date}` $\rightarrow$ Target publication date (`YYYY-MM-DD`).
- `{time}` $\rightarrow$ Scheduled publication time (`HH:MM`).
- `{month}` / `{month_name}` $\rightarrow$ Two-digit month and full month name (e.g. `August`).
- `{year}` $\rightarrow$ 4-digit calendar year (e.g. `2026`).

---

### 2.2 Scheduling Modes & Leap-Year Resolution

1. **Day-of-Month Mode (`DOM`)**:
   - Matches filename day indices (1–31) with the target calendar day.
   - **30-Day Month Handling**: On the 31st of months with only 30 days (April, June, Sept, Nov), falls back to day 30.
   - **Leap Year Handling (February)**:
     - On February 29 during non-leap years (2025, 2026, 2027), falls back to February 28.
     - On February 29 during leap years (2024, 2028, 2032), matches the `29` video asset.
     - On February 30 and 31, falls back to the last valid day of February.

2. **Rotation Mode (`ROT`)**:
   - Deterministic sequential video queue.
   - Preserves state in `rotation_states` table (`current_index`, `last_video_id`).
   - Automatically loops back to index 0 upon reaching the end of the folder queue.

3. **Shuffle Mode (`SHUF`)**:
   - True non-repeating randomized queue.
   - Shuffles all available video IDs into `remaining_video_ids`.
   - Once all videos are exhausted, increments `current_cycle` and reshuffles a fresh batch.

4. **Repeat Mode (`REP`)**:
   - Continuously schedules a single designated video across every recurrence without state drift.

---

### 2.3 Concurrency Control & Worker Pool (`UploadWorkerPool`)

- **Global Concurrency Semaphore**: Defaults to max 3 concurrent uploads to prevent VPS network congestion.
- **Per-Channel Mutex Locks**: Enforces strict single-upload serialization per channel (`asyncio.Lock`) to prevent YouTube API race conditions and out-of-order `publishAt` collisions.
- **Anti-Burst Cooldown**: Imposes a 5-second cooldown timer between consecutive uploads on the same channel.
- **Circuit Breaker / Queue Pause**: Admins can pause the upload queue instantly (`POST /api/v1/uploads/queue/pause`).

---

### 2.4 Reliability, Retries & Crash Reconciliation

- **Idempotency Key**: Generated as `{schedule_id}:{target_date_iso}`. Prevents duplicate uploads of the same video recurrence even if triggers overlap.
- **Error Classifier**:
  - *Transient Errors* (500/502/503 HTTP gateway errors, connection timeouts, rate limit hits): Automatically scheduled for exponential backoff retry ($\min(300s, \text{base} \times 2^{\text{retry}} + \text{jitter})$).
  - *Fatal Errors* (OAuth token revoked, YouTube quota exceeded, invalid video format): Marked as `FAILED` immediately without burning unnecessary retries.
- **Startup Crash Reconciliation**:
  - Automatically executed in FastAPI lifespan on container startup.
  - Scans database for `IN_PROGRESS` or `RETRYING` jobs interrupted by server reboots.
  - Removes abandoned temporary chunk files (`/app/temp/*.mp4`) on disk.
  - Resets retryable occurrences back to `QUEUED`.

---

## 3. Database Schema Overview

```
+---------------+       +------------------+       +---------------+
|   channels    | 1---N | content_folders  | 1---N |    videos     |
+---------------+       +------------------+       +---------------+
| id (UUID)     |       | id (UUID)        |       | id (UUID)     |
| name          |       | channel_id       |       | channel_id    |
| timezone      |       | storage_folder_id|       | folder_id     |
| templates     |       | name, path       |       | filename, path|
+-------+-------+       +------------------+       | day_of_month  |
        |                                          | metadata, etc.|
        | 1---N                                    +-------+-------+
        v                                                  |
+---------------+                                          |
|   schedules   | 1---N                                    |
+---------------+                                          |
| id (UUID)     |                                          |
| channel_id    |                                          |
| mode (DOM/ROT)|                                          |
| publish_time  |                                          |
| lead_minutes  |                                          |
+-------+-------+                                          |
        |                                                  |
        | 1---N                                            |
        v                                                  v
+----------------------------------------------------------+
|                  schedule_occurrences                    |
+----------------------------------------------------------+
| id (UUID), schedule_id, channel_id, video_id             |
| idempotency_key (UNIQUE)                                 |
| scheduled_publish_time (TIMESTAMPTZ)                     |
| target_upload_time (TIMESTAMPTZ)                         |
| status (QUEUED, UPLOADING, COMPLETED, RETRYING, FAILED)  |
| youtube_video_id, youtube_watch_url                      |
+----------------------------------------------------------+
```
