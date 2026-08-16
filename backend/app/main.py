import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import setup_logging, logger
from app.core.database import async_engine, Base
from app.api.v1.api import api_router
from app.services.scheduler.scheduler_engine import SchedulerEngine
from app.services.worker.recovery import ReconciliationService

# Configure logging
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing YouTube Video Automation & Scheduling Platform...")
    # Ensure temporary and storage directories exist
    os.makedirs(settings.TEMP_STORAGE_PATH, exist_ok=True)
    os.makedirs(settings.LOCAL_STORAGE_BASE_PATH, exist_ok=True)

    # Initialize Database Tables (for dev/SQLite)
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database schema initialized successfully.")

    # Initialize APScheduler engine
    await SchedulerEngine.start()

    # Run Crash Reconciliation scan on startup
    try:
        recon_summary = await ReconciliationService.reconcile_orphaned_jobs()
        logger.info(f"Startup crash reconciliation finished: {recon_summary}")
    except Exception as recon_err:
        logger.warning(f"Could not complete startup crash reconciliation: {recon_err}")

    yield

    logger.info("Shutting down application...")
    await SchedulerEngine.shutdown()
    await async_engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan
)

# Set up CORS
if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include API v1 Router
app.include_router(api_router, prefix="/api/v1")

# Serve React Frontend SPA if built dist directory exists
frontend_candidates = [
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")),
    os.path.abspath("/app/frontend/dist"),
    os.path.abspath("./frontend/dist"),
]
dist_dir = next((p for p in frontend_candidates if os.path.exists(p)), None)

if dist_dir:
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse

    assets_dir = os.path.join(dist_dir, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Don't intercept API routes
        if full_path.startswith("api/"):
            return {"error": "Not Found"}
        target_file = os.path.join(dist_dir, full_path)
        if full_path and os.path.exists(target_file) and os.path.isfile(target_file):
            return FileResponse(target_file)
        return FileResponse(os.path.join(dist_dir, "index.html"))
else:
    @app.get("/")
    async def root():
        return {
            "message": "YouTube Video Automation & Scheduling Platform API",
            "docs": "/api/docs",
            "health": "/api/v1/health"
        }
