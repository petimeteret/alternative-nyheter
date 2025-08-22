from fastapi import FastAPI, Depends, Query, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc, distinct
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
import structlog
import traceback
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from .db import Base, engine, SessionLocal
from .models import Article
from .schemas import ArticleOut, Paginated
from .fetcher import fetch_and_store
from .config import settings

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO level
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="AlternativeNyheter API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"]
)

Base.metadata.create_all(bind=engine)

# Mount static files for single-container deployment
import os
if os.path.exists("static"):
    app.mount("/", StaticFiles(directory="static", html=True), name="static")

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        "Unhandled exception",
        exc_info=exc,
        path=request.url.path,
        method=request.method,
        traceback=traceback.format_exc()
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "path": request.url.path}
    )

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    try:
        # Test database connection
        db = SessionLocal()
        db.execute(select(1))
        db.close()
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error("Health check failed", exc_info=e)
        raise HTTPException(status_code=503, detail="Service unhealthy")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

sched = BackgroundScheduler()
@sched.scheduled_job('interval', minutes=settings.FETCH_INTERVAL_MIN)
def scheduled_fetch():
    db = SessionLocal()
    try:
        fetch_and_store(db)
    finally:
        db.close()

sched.start()

@app.get("/api/articles", response_model=Paginated)
@limiter.limit("30/minute")
def list_articles(
    request: Request,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    source: str | None = None,
    sources: str | None = None,  # comma-separated list
    category: str | None = None,
    language: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    q: str | None = None,
):
    stmt = select(Article)
    if source:
        stmt = stmt.where(Article.source_domain == source)
    if sources:
        source_list = [s.strip() for s in sources.split(',')]
        stmt = stmt.where(Article.source_domain.in_(source_list))
    if category:
        stmt = stmt.where(Article.theme == category)
    if language:
        stmt = stmt.where(Article.language == language)
    if date_from:
        stmt = stmt.where(Article.published_at >= date_from)
    if date_to:
        stmt = stmt.where(Article.published_at <= date_to)
    if q:
        like = f"%{q}%"
        stmt = stmt.where((Article.title.ilike(like)) | (Article.summary.ilike(like)))
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    stmt = stmt.order_by(desc(Article.published_at)).offset((page-1)*page_size).limit(page_size)
    items = db.scalars(stmt).all()
    out = [
        ArticleOut(
            id=a.id,
            title=a.title,
            summary=a.summary,
            author=a.author,
            published_at=a.published_at,
            source_name=a.source_name,
            source_url=f"https://{a.source_domain}",
            article_url=a.url,
            language=a.language,
            theme=a.theme,
        ) for a in items
    ]
    return Paginated(items=out, total=total or 0, page=page, page_size=page_size)

@app.get("/api/categories")
@limiter.limit("60/minute")
def get_categories(request: Request, db: Session = Depends(get_db)):
    categories = db.scalars(
        select(distinct(Article.theme))
        .where(Article.theme.is_not(None))
        .order_by(Article.theme)
    ).all()
    return {"categories": categories}

@app.get("/api/sources")
@limiter.limit("60/minute")
def get_sources(request: Request, db: Session = Depends(get_db)):
    sources = db.scalars(
        select(distinct(Article.source_domain))
        .order_by(Article.source_domain)
    ).all()
    return {"sources": sources}

@app.post("/api/refresh")
@limiter.limit("2/minute")  # More restrictive for expensive operation
async def manual_refresh(request: Request, db: Session = Depends(get_db)):
    try:
        # Run fetch in background to avoid timeout
        import asyncio
        import threading
        
        def run_fetch():
            fetch_and_store(db)
        
        # Start fetch in background thread
        thread = threading.Thread(target=run_fetch)
        thread.start()
        
        return {"status": "refresh_started", "message": "Oppdatering startet i bakgrunnen"}
    except Exception as e:
        logger.error("Error starting refresh", exc_info=e)
        return {"status": "error", "message": "Kunne ikke starte oppdatering"}
