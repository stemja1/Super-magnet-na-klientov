"""FastAPI application entrypoint for Super magnet na klientov."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, embeddings, leads, llm
from app.config import settings
from app.db.session import init_db

logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
logger = logging.getLogger("supermagnet")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("Database initialized")
    yield


app = FastAPI(
    title="Super magnet na klientov — Backend API",
    description=(
        "Lokálny, open-source Apollo.io klon optimalizovaný pre slovenský B2B trh "
        "(ORSR, FinStat, Živnostenský register). Všetka LLM inference prebieha lokálne."
    ),
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(llm.router, prefix="/api")
app.include_router(auth.router)
app.include_router(leads.router)
app.include_router(embeddings.router)


@app.get("/health", tags=["system"])
def health():
    return {
        "status": "ok",
        "llm_backend": llm.orchestrator.backend,
        "version": "0.2.0",
    }


@app.get("/", tags=["system"])
def root():
    return {"name": "Super magnet na klientov", "docs": "/docs", "health": "/health"}
