"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import init_db, close_db
from app.rag import rag_service
from app.api import courses, runs, topics, quizzes, progress, uploads

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting StudyCrew backend...")
    await init_db()
    await rag_service.initialize()
    logger.info("Backend ready")

    yield

    # Shutdown
    logger.info("Shutting down...")
    await rag_service.close()
    await close_db()


app = FastAPI(
    title="StudyCrew API",
    description="Multi-agent study planner API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(courses.router, prefix="/api/courses", tags=["courses"])
app.include_router(runs.router, prefix="/api/runs", tags=["runs"])
app.include_router(topics.router, prefix="/api/topics", tags=["topics"])
app.include_router(quizzes.router, prefix="/api/quizzes", tags=["quizzes"])
app.include_router(progress.router, prefix="/api/courses", tags=["progress"])
app.include_router(uploads.router, prefix="/api/courses", tags=["uploads"])


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/")
async def root():
    return {"name": "StudyCrew API", "version": "0.1.0"}