"""
INSPECTRA Backend — Application Entry Point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os

from app.core.config import settings
from app.core.database import init_db
from app.api import auth, users, products, inspections, images, dashboard


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: initialise DB tables. Shutdown: nothing to clean up yet."""
    init_db()
    # Ensure local upload directory exists when using local storage backend
    if settings.STORAGE_BACKEND == "local":
        os.makedirs(settings.LOCAL_UPLOAD_DIR, exist_ok=True)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-Powered Legal Metrology Inspection System — FastAPI Backend",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static file serving for local uploads ─────────────────────────────────────
# NOTE: In production replace with a CDN / object storage signed URL.
if settings.STORAGE_BACKEND == "local":
    os.makedirs(settings.LOCAL_UPLOAD_DIR, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=settings.LOCAL_UPLOAD_DIR), name="uploads")

# ── API Routers ───────────────────────────────────────────────────────────────
API_PREFIX = "/api"

app.include_router(auth.router,        prefix=f"{API_PREFIX}/auth",        tags=["Authentication"])
app.include_router(users.router,       prefix=f"{API_PREFIX}/users",       tags=["Users"])
app.include_router(products.router,    prefix=f"{API_PREFIX}/products",    tags=["Products"])
app.include_router(inspections.router, prefix=f"{API_PREFIX}/inspections", tags=["Inspections"])
app.include_router(images.router,      prefix=f"{API_PREFIX}/inspections", tags=["Inspection Images"])
app.include_router(dashboard.router,   prefix=f"{API_PREFIX}/dashboard",   tags=["Dashboard"])


@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}
