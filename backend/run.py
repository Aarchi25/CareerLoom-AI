import uvicorn
from backend.config import settings

if __name__ == "__main__":
    print(f"[RUN] Starting Uvicorn server on http://localhost:{settings.PORT}")
    print(f"[DOCS] Swagger UI docs available at: http://localhost:{settings.PORT}/docs")
    uvicorn.run("backend.main:app", host=settings.HOST, port=settings.PORT, reload=True)
