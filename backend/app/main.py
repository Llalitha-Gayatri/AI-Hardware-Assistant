"""FastAPI main application entrypoint."""
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.api.routes import router as api_router
from app.config import settings

app = FastAPI(
    title="Linux Hardware AI Assistant API",
    description="Intelligent natural-language Q&A interface for Linux hardware inspection with safe LLM tool calling.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS for flexible frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS if settings.ALLOWED_ORIGINS != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API endpoints
app.include_router(api_router)

# Mount frontend files for convenience
frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_index():
        """Serve the frontend single-page dashboard."""
        index_file = frontend_dir / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return {"message": "Frontend index.html not found"}

    @app.get("/style.css", include_in_schema=False)
    async def serve_css():
        """Serve frontend stylesheet."""
        css_file = frontend_dir / "style.css"
        if css_file.exists():
            return FileResponse(str(css_file), media_type="text/css")
        return {"message": "style.css not found"}

    @app.get("/script.js", include_in_schema=False)
    async def serve_js():
        """Serve frontend client script."""
        js_file = frontend_dir / "script.js"
        if js_file.exists():
            return FileResponse(str(js_file), media_type="application/javascript")
        return {"message": "script.js not found"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
