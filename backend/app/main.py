from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import upload, analyze, avatar, generate, status, share, health, queue

app = FastAPI(title="Gemini Motion Lab API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, prefix="/api")
app.include_router(analyze.router, prefix="/api")
app.include_router(avatar.router, prefix="/api")
app.include_router(generate.router, prefix="/api")
app.include_router(status.router, prefix="/api")
app.include_router(share.router, prefix="/api")
app.include_router(share.html_router)
app.include_router(health.router, prefix="/api")
app.include_router(queue.router, prefix="/api")

