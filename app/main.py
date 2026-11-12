"""SocialRadar application entry point.

Run with:  uvicorn app.main:app --reload
"""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api import demo, matches, notifications, posts, stats, trackers
from app.errors import AppError

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(
    title="SocialRadar API",
    version="0.1.0",
    description=(
        "Find potential clients in social media posts.\n\n"
        "Create **trackers** with keywords, add **posts**, and the API creates "
        "**matches** (leads) and **notifications** automatically.\n\n"
        "All data is kept in memory and is reset when the server restarts. "
        "Posts are added manually or from a demo set; no real Bluesky or "
        "Threads data is loaded in this version."
    ),
    openapi_tags=[
        {"name": "Trackers", "description": "Keyword trackers (Workflow 1)"},
        {"name": "Posts", "description": "Post ingestion and matching (Workflow 2)"},
        {"name": "Matches / Leads", "description": "Found leads and their status (Workflow 3)"},
        {"name": "Notifications", "description": "Created automatically for each new match"},
        {"name": "Other", "description": "Stats, health check, demo data"},
    ],
)


@app.exception_handler(AppError)
def handle_app_error(request: Request, error: AppError) -> JSONResponse:
    """Turn business errors from services into JSON like {"detail": "..."}."""
    return JSONResponse(status_code=error.status_code, content={"detail": error.message})


app.include_router(trackers.router)
app.include_router(posts.router)
app.include_router(matches.router)
app.include_router(notifications.router)
app.include_router(stats.router)
app.include_router(demo.router)

# Frontend: static files plus index.html on the root URL.
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")
