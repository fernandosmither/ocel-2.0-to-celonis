import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from config import settings
from celonis.router import router as celonis_router, session_manager, cleanup_task
from cloudflare.router import router as cloudflare_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    cleanup_task_handle = asyncio.create_task(cleanup_task())
    yield
    cleanup_task_handle.cancel()
    for session_id in list(session_manager.sessions.keys()):
        await session_manager.cleanup_session(session_id)


env_config = {
    "lifespan": lifespan,
    "docs_url": "/docs" if settings.ENVIRONMENT == "development" else None,
    "redoc_url": "/redoc" if settings.ENVIRONMENT == "development" else None,
    "openapi_url": "/openapi.json" if settings.ENVIRONMENT == "development" else None,
}

app = FastAPI(**env_config)


@app.get("/")
async def get():
    return {"message": "Celonis WebSocket API"}


app.include_router(celonis_router)
app.include_router(cloudflare_router)
