import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import router


def _cors_origins() -> list[str]:
    raw = os.environ.get(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:4173,http://127.0.0.1:4173",
    )
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


app = FastAPI(
    title="CodeAtlas",
    description="Static analysis, semantic retrieval, and grounded Q&A for Python GitHub repositories.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.get("/")
def root():
    return {
        "name": "CodeAtlas",
        "docs": "/docs",
    }
