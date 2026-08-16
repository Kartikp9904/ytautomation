# REST API Reference Manual

The **YouTube Video Scheduling & Automation Platform** exposes a comprehensive FastAPI REST API under `/api/v1/`.

---

## 1. Authentication & System Diagnostics

### Health Check
- **Endpoint**: `GET /api/v1/health`
- **Description**: Returns backend operational status, active database dialect, and scheduler status.
- **Response `200 OK`**:
```json
{
  "status": "healthy",
  "app_name": "YouTube Video Automation Platform",
  "version": "1.0.0",
  "database": "sqlite",
  "scheduler_running": true
}
```

### Timezone Listing
- **Endpoint**: `GET /api/v1/channels/timezones`
- **Description**: Returns all standard IANA timezone identifiers (e.g. `America/New_York`, `UTC`, `Asia/Tokyo`).
- **Response `200 OK`**:
```json
["UTC", "America/New_York", "America/Los_Angeles", "Europe/London", "Asia/Tokyo", "..."]
```

---

## 2. Channel Management (`/api/v1/channels`)

### List Channels
- **Endpoint**: `GET /api/v1/channels`
- **Response `200 OK`**:
```json
{
  "channels": [
    {
      "id": "c71e21b4-...",
      "name": "Daily Tech Shorts",
      "timezone": "America/New_York",
      "is_active": true,
      "default_title_template": "{channel} - {title}",
      "default_category_id": "28",
      "default_privacy_status": "private",
      "youtube_channel_name": "Tech Highlights",
      "youtube_custom_url": "@techhighlights",
      "is_youtube_connected": true
    }
  ],
  "total": 1
}
```

### Create Channel
- **Endpoint**: `POST /api/v1/channels`
- **Body**:
```json
{
  "name": "Daily Tech Shorts",
  "timezone": "America/New_York",
  "default_title_template": "{channel} - Daily Tech Review #{day}",
  "default_description_template": "Follow us for daily updates! Published on {date}.",
  "default_tags": ["tech", "gadgets", "daily"],
  "default_category_id": "28",
  "default_privacy_status": "private"
}
```

---

## 3. Google Drive Integration (`/api/v1/drive`)

### Get Drive OAuth Authorization URL
- **Endpoint**: `GET /api/v1/drive/oauth/url`
- **Response `200 OK`**:
```json
{
  "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?..."
}
```

### List Google Drive Folders
- **Endpoint**: `GET /api/v1/drive/folders?parent_id=root`
- **Response `200 OK`**:
```json
[
  {
    "id": "1A2B3C...",
    "name": "YouTube Content 2026",
    "mime_type": "application/vnd.google-apps.folder"
  }
]
```

### Index Content Folder
- **Endpoint**: `POST /api/v1/drive/folders/index`
- **Body**:
```json
{
  "channel_id": "c71e21b4-...",
  "storage_folder_id": "1A2B3C...",
  "folder_name": "YouTube Content 2026",
  "recursive": true
}
```

---

## 4. Video Library & Metadata Preview (`/api/v1/videos`)

### List Ingested Videos
- **Endpoint**: `GET /api/v1/videos?channel_id=...&folder_id=...&search=day`
- **Response `200 OK`**:
```json
{
  "videos": [
    {
      "id": "v9928...",
      "filename": "15_tech_review.mp4",
      "path": "/YouTube Content 2026/15_tech_review.mp4",
      "day_of_month_index": 15,
      "effective_title": "Daily Tech Shorts - Daily Tech Review #15",
      "enabled": true
    }
  ],
  "total": 1
}
```

### Preview Effective Metadata
- **Endpoint**: `GET /api/v1/videos/{id}/metadata-preview?target_datetime=2026-08-15T19:00:00Z`
- **Response `200 OK`**:
```json
{
  "title": "Daily Tech Shorts - Daily Tech Review #15",
  "description": "Follow us for daily updates! Published on 2026-08-15.",
  "tags": ["tech", "gadgets", "daily"],
  "category_id": "28",
  "privacy_status": "private",
  "resolved_from": "CHANNEL_TEMPLATE"
}
```

---

## 5. Automation Schedules (`/api/v1/schedules`)

### Create Schedule
- **Endpoint**: `POST /api/v1/schedules`
- **Body**:
```json
{
  "channel_id": "c71e21b4-...",
  "name": "Evening Prime Upload",
  "schedule_type": "DAILY",
  "source_type": "FOLDER",
  "source_id": "f8821...",
  "mode": "DAY_OF_MONTH",
  "publish_time": "18:00",
  "timezone": "America/New_York",
  "upload_lead_minutes": 180,
  "use_youtube_scheduled_publish": true,
  "dry_run": false,
  "enabled": true
}
```

### Dry-Run Calendar Simulator
- **Endpoint**: `POST /api/v1/schedules/{id}/simulate-calendar?year=2026&month=8`
- **Response `200 OK`**:
```json
{
  "schedule_id": "s1129...",
  "schedule_name": "Evening Prime Upload",
  "year": 2026,
  "month": 8,
  "total_days": 31,
  "days": [
    {
      "day": 1,
      "date": "2026-08-01",
      "is_matched": true,
      "video_filename": "01_intro.mp4",
      "is_fallback": false
    }
  ]
}
```

### Today's Timeline
- **Endpoint**: `GET /api/v1/schedules/timeline/today`
- **Response `200 OK`**:
```json
[
  {
    "occurrence_id": "occ_881...",
    "schedule_id": "s1129...",
    "schedule_name": "Evening Prime Upload",
    "channel_id": "c71e21b4-...",
    "channel_name": "Daily Tech Shorts",
    "video_title": "Daily Tech Review #15",
    "scheduled_publish_time": "2026-08-15T18:00:00-04:00",
    "status": "QUEUED"
  }
]
```

---

## 6. YouTube Integration & Upload Management (`/api/v1/youtube` & `/api/v1/uploads`)

### Check Daily Quota
- **Endpoint**: `GET /api/v1/youtube/quota-status?channel_id=...`
- **Response `200 OK`**:
```json
{
  "daily_quota_limit": 10000,
  "used_units": 1600,
  "remaining_units": 8400,
  "used_percentage": 16.0,
  "can_upload": true
}
```

### Trigger Manual "Upload Now"
- **Endpoint**: `POST /api/v1/uploads/manual`
- **Body**:
```json
{
  "video_id": "v9928...",
  "channel_id": "c71e21b4-...",
  "custom_title": "Special Live Showcase",
  "privacy_status": "private",
  "dry_run": false
}
```

### Worker Pool Diagnostics & Queue Controls
- **Endpoint**: `GET /api/v1/uploads/queue/status`
- **Endpoint**: `POST /api/v1/uploads/queue/pause`
- **Endpoint**: `POST /api/v1/uploads/queue/resume`
- **Endpoint**: `POST /api/v1/uploads/{job_id}/retry`
- **Endpoint**: `POST /api/v1/uploads/reconcile`
