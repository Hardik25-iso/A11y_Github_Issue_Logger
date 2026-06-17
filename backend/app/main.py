from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import get_settings
from backend.app.routers import generation, github, scan, system

load_dotenv()
settings = get_settings()

app = FastAPI(title="A11y GitHub Issue Logger API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(system.router)
app.include_router(scan.router)
app.include_router(github.router)
app.include_router(generation.router)
