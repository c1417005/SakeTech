"""KUMU backend entrypoint.

Run:  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
Docs: http://localhost:8000/docs
Demo (mock sessions): GET /sessions?mock=true  or  KUMU_MOCK=true
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import db
from app.routes import router

app = FastAPI(title="KUMU Backend", version="0.1.0")

# Frontend (Vite dev server, separate origin) calls these APIs.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten for production
    allow_methods=["*"],
    allow_headers=["*"],
)

db.init_db()


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(router)
