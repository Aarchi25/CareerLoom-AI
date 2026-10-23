from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from backend.config import settings
from backend.database import get_connection_status, get_mongo_db
from backend.routers import auth, chat, resume, health


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: test MongoDB connection
    print("=" * 60)
    print("[INIT] Starting CareerLoom AI Backend (FastAPI)")
    print("=" * 60)
    status = get_connection_status()
    print(f"[DB] Active Database Backend: {status['active_backend']}")
    print(f"[NET] Current Public IP:       {status['current_public_ip']}")
    if not status["mongodb_connected"]:
        print("[WARN] MongoDB Atlas is not yet connected.")
        print("[INFO] Whitelist your IP in MongoDB Atlas: Security > Network Access")
    else:
        print("[OK] MongoDB Atlas connected successfully!")
    print("=" * 60)
    yield
    print("[STOP] Shutting down CareerLoom AI Backend.")


app = FastAPI(
    title="CareerLoom AI API",
    description="Backend REST API for CareerLoom AI - Weaving Skills into Career Opportunities.",
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routers
app.include_router(health.router, prefix=settings.API_V1_STR)
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(chat.router, prefix=settings.API_V1_STR)
app.include_router(resume.router, prefix=settings.API_V1_STR)


@app.get("/", include_in_schema=False)
def root():
    """Redirect root path to interactive Swagger documentation."""
    return RedirectResponse(url="/docs")
