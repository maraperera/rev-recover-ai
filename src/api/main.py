from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import audit, health


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup actions on startup
    yield
    # Teardown actions on shutdown


app = FastAPI(
    title="RevRecover AI - Enterprise Financial Audit Engine",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(audit.router, prefix="/api/v1/audits", tags=["Audits"])