from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db import Base, engine
from .routers import ai, attempts, auth, courses, exams, exercises, users


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Suffisant pour un template. En production : migrations Alembic.
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="Edu IA", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

for r in (auth, users, courses, exercises, exams, attempts, ai):
    app.include_router(r.router)


@app.get("/health", tags=["système"])
def health():
    return {"status": "ok", "llm_provider": settings.llm_provider}
