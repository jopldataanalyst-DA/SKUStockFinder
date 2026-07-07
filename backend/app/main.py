import logging
import threading
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import db
from .config import settings
from .scheduler import run_fetch_job, scheduler, start_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("skufinder.main")

app = FastAPI(title="SKUFinder API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    start_scheduler()
    # kick off an immediate fetch in the background so data is fresh on first load
    threading.Thread(target=_safe_run_fetch_job, daemon=True).start()


@app.on_event("shutdown")
def on_shutdown() -> None:
    scheduler.shutdown(wait=False)


def _safe_run_fetch_job() -> None:
    try:
        run_fetch_job()
    except Exception:
        logger.exception("Initial fetch job failed")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/skus")
def list_skus(q: str | None = Query(default=None), limit: int = Query(default=100, le=1000)) -> list[dict]:
    return db.search_skus(q, limit)


@app.post("/refresh")
def refresh() -> dict:
    count = run_fetch_job()
    return {"rows_upserted": count}


# When the frontend build is bundled alongside the backend in a single
# container, serve it here so one process handles both API and static assets.
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
