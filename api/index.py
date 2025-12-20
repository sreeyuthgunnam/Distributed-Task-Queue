"""Vercel entry point for FastAPI application."""
import sys
import os

# Add the project root to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from src.api.main import app
    
    # Vercel expects 'app' or 'handler' to be exported
    handler = app
    
except Exception as e:
    # If import fails, create a minimal FastAPI app to show the error
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    
    app = FastAPI()
    handler = app
    
    @app.get("/")
    @app.get("/api")
    @app.get("/api/health")
    async def error_handler():
        return JSONResponse(
            status_code=500,
            content={
                "error": "Failed to initialize application",
                "detail": str(e),
                "type": type(e).__name__,
                "hint": "Check Vercel logs and ensure all dependencies are installed"
            }
        )
