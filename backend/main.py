"""
NinjaMediaManager - FastAPI Backend
Main application entry point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from pathlib import Path

from backend.api.routes import files, media, subtitles, tasks

# Create FastAPI app
app = FastAPI(
    title="NinjaMediaManager",
    description="Media management tool with subtitle processing capabilities",
    version="0.1.0",
)

# CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(files.router, prefix="/api/files", tags=["files"])
app.include_router(media.router, prefix="/api/media", tags=["media"])
app.include_router(subtitles.router, prefix="/api/subtitles", tags=["subtitles"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "0.1.0",
        "media_path": os.environ.get("MEDIA_PATH", "/media"),
        "output_path": os.environ.get("OUTPUT_PATH", "/output"),
    }


# Serve static files (React frontend) in production
static_path = Path(__file__).parent.parent / "static"
if static_path.exists():
    app.mount("/assets", StaticFiles(directory=static_path / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve the React SPA for all non-API routes"""
        file_path = static_path / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(static_path / "index.html")
