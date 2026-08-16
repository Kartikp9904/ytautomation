# YouTube Video Scheduling & Automation Platform

A production-ready, self-hosted multi-channel YouTube video scheduling and automation system powered by FastAPI, SQLAlchemy, React 18, Google Drive API, and YouTube Data API v3.

---

## 🚀 System Architecture Overview

```
Client Web Browser  <--->  Host Nginx (HTTPS / Certbot SSL / Rate Limiting)
                                  |
            +---------------------+---------------------+
            | (Port 80)                                 | (Port 8000)
    Frontend Container (React/Vite SPA)         Backend Container (FastAPI REST API)
                                                        |
                                    +-------------------+-------------------+
                                    |                   |                   |
                               APScheduler          Database         StorageProvider
                                    |            (SQLite / Postgres)        |
                            UploadWorkerPool                                +--> Google Drive API v3
                                    |                                       +--> LocalStorage (Dev)
                         ReconciliationService
                                    |
                                    +--> YouTube Data API v3 (Resumable Upload & Thumbnail Set)
```

---

## 📦 Project Structure

```
ytvideosautomation/
│
├── backend/
│   ├── alembic/              # Database migration scripts
│   ├── app/
│   │   ├── api/v1/
│   │   │   ├── endpoints/
│   │   │   │   ├── health.py     # Health & system diagnostics
│   │   │   │   ├── auth.py       # JWT & password auth
│   │   │   │   ├── channels.py   # Channel CRUD & timezones
│   │   │   │   ├── drive.py      # Drive OAuth, folder browsing & indexing
│   │   │   │   ├── videos.py     # Video listing, filter & metadata preview
│   │   │   │   ├── folders.py    # Folder settings & default templates
│   │   │   │   ├── schedules.py  # Automation schedules, timeline, calendar events, rotation & shuffle
│   │   │   │   ├── youtube.py    # YouTube OAuth2 flow, verification, disconnect & quota status
│   │   │   │   └── uploads.py    # Manual uploads, progress tracking, retry, reconcile & worker pool queue status
│   │   │   └── api.py
│   │   ├── core/             # Database engine, AES encryption, JWT, logging, config
│   │   ├── models/           # SQLAlchemy 2.0 models (Channel, Video, Folder, Schedule, States, OAuth...)
│   │   ├── schemas/          # Pydantic v2 schemas
│   │   ├── services/
│   │   │   ├── storage/      # StorageProvider interface, LocalStorage, GoogleDriveStorage
│   │   │   ├── google_drive/ # Drive OAuth2 flow & token manager
│   │   │   ├── scanner/      # Recursive scanner, day-of-month parser, sidecar JSON/thumbnail resolver
│   │   │   ├── metadata/     # MetadataEngine (5-tier priority hierarchy & template variables)
│   │   │   ├── scheduler/    # SchedulerEngine (APScheduler, multi-frequency triggers, timezone precision)
│   │   │   │   └── modes/    # DayOfMonthResolver, RepeatModeResolver, RotationModeResolver, ShuffleModeResolver
│   │   │   ├── youtube/      # YouTubeOAuthService, YouTubeQuotaTracker, YouTubeUploaderService
│   │   │   ├── worker/       # UploadWorkerPool, ErrorClassifier, RetryEngine, ReconciliationService
│   │   │   └── channel_service.py
│   │   ├── Dockerfile        # Production multi-stage backend container
│   │   ├── entrypoint.sh     # Auto-migration & uvicorn entrypoint
│   │   └── main.py           # FastAPI entrypoint & lifespan
│   ├── tests/                # Automated pytest suite (45 tests)
│   ├── requirements.txt      # Python dependencies
│   └── alembic.ini
│
├── frontend/
│   ├── src/
│   │   ├── api/              # Axios client (health, channels, drive, videos, schedules, youtube, uploads)
│   │   ├── components/
│   │   │   ├── layout/       # Navbar, Sidebar, Layout
│   │   │   ├── channels/     # ChannelCard (with YouTube OAuth & Quota progress), ChannelModal
│   │   │   ├── videos/       # MetadataPreviewModal, UploadNowModal
│   │   │   ├── schedules/    # ScheduleModal (Lead Time & publishAt), CalendarPreviewModal
│   │   │   └── dashboard/    # WorkerPoolWidget
│   │   ├── pages/            # Dashboard, Channels, Drive, Library, Schedules, Calendar, LogsPage
│   │   ├── constants/        # YouTube Categories
│   │   ├── App.tsx           # React Router
│   │   └── index.css         # Tailwind CSS styling & dark theme
│   ├── Dockerfile            # Production multi-stage frontend container
│   ├── nginx.conf            # Nginx SPA reverse proxy & gzip configuration
│   └── package.json
│
├── docs/
│   ├── ARCHITECTURE.md       # Technical specs, diagrams, scheduling algorithms
│   ├── API_REFERENCE.md      # REST API endpoints & JSON payloads
│   ├── OPERATIONS_AND_TROUBLESHOOTING.md # Maintenance, quotas, backups
│   └── USER_GUIDE.md         # End-user tutorials & workflow guides
│
├── deploy/
│   ├── DEPLOYMENT_GUIDE.md   # Step-by-step VPS installation & hardening guide
│   ├── setup-vps.sh          # 1-click automated Ubuntu provisioning script
│   ├── backup.sh             # Automated SQLite & credential backup script
│   ├── nginx/
│   │   └── yt-automation.conf # Host reverse proxy with TLS & rate limiting
│   ├── fail2ban/
│   │   └── jail.local        # Intrusion prevention jail configurations
│   └── systemd/
│       └── ytvideosautomation.service # Auto-start service on boot
│
├── docker-compose.yml        # Standard multi-container compose
├── docker-compose.prod.yml   # Production compose with PostgreSQL
├── .dockerignore             # Container build exclusions
├── .env.docker.example       # Container environment template
├── .env.example              # Local environment variables template
├── .gitignore                # Git ignore patterns
└── README.md
```

---

## ⚡ 1-Click Ubuntu VPS Deployment

```bash
# On a fresh Ubuntu 22.04 / 24.04 VPS:
git clone https://github.com/your-username/ytvideosautomation.git /opt/ytvideosautomation
cd /opt/ytvideosautomation
sudo bash deploy/setup-vps.sh
```

See [Deployment Guide](file:///c:/Users/Genie/Downloads/CODING/ytvideosautomation/deploy/DEPLOYMENT_GUIDE.md) for full instructions.

---

## 🛠️ Local Development (Windows 11)

### 1. Backend Setup (FastAPI & Python 3.12+)

```powershell
# In ytvideosautomation\backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend Setup (React, Vite, Tailwind CSS)

```powershell
# In ytvideosautomation\frontend
npm install
npm run dev
```

Web Dashboard: `http://localhost:5173`

---

## 🧪 Automated Tests

Run backend test suite:
```powershell
cd backend
.\venv\Scripts\pytest.exe -v
```

---

## 📋 Implementation Progress (100% Complete)

- [x] **Phase 1**: Architecture, Project Skeleton, FastAPI, React/Vite, Database Models, Security & Config.
- [x] **Phase 2**: Channel Management, Timezones, Default Templates & Dashboard Integration.
- [x] **Phase 3**: Google Drive Integration, Storage Abstraction, Folder Browser & File Scanner.
- [x] **Phase 4**: Video Library & Sidecar Metadata / Thumbnails.
- [x] **Phase 5**: Core Scheduler Engine (APScheduler, Multi-Frequency & Timezone Rules).
- [x] **Phase 6**: Day-of-Month Mapping Logic (Leap years, 30-day checks & Calendar Simulator).
- [x] **Phase 7**: Repeat Mode (Continuous Single-Video Scheduling & Loop Rules).
- [x] **Phase 8**: Rotation Mode (Sequential Video Queue & Persistent State Tracker).
- [x] **Phase 9**: Shuffle Mode (Non-Repeating Randomized Queue & Cycle Tracker).
- [x] **Phase 10**: YouTube OAuth Multi-Channel Integration (Channel Verification, Token Refresh & Quota Management).
- [x] **Phase 11**: Manual YouTube Upload ("Upload Now").
- [x] **Phase 12**: Automated YouTube Scheduled Upload (`publishAt` ISO 8601 & Lead Time Buffer).
- [x] **Phase 13**: Multi-Channel Concurrency (Worker Pool, Per-Channel Rate Limiter & Concurrency Limits).
- [x] **Phase 14**: Duplicate Protection, Retries, Exponential Backoff & Crash Reconciliation.
- [x] **Phase 15**: Polished Dashboard, Calendar View & Dry-Run Simulator.
- [x] **Phase 16**: Containerization (Docker & Compose).
- [x] **Phase 17**: Ubuntu VPS Deployment, Nginx, HTTPS & Hardening.
- [x] **Phase 18**: End-to-End Testing & Documentation.
