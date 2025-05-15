from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.routes import api, embeddings, auth, google_auth, twitter, facebook

app = FastAPI(
    title="AI Content Generation Backend",
    description="Backend for AI-powered content generation using RAG with OpenAI, LangChain, and Supabase",
    version="1.0.0"
)

# Enable CORS - cụ thể các origin được phép
origins = [
    "http://localhost:8080",    # Landing page URL
    "http://127.0.0.1:8080",    # Landing page URL (IP)
    "http://localhost:3000",    # Dashboard URL
    "http://127.0.0.1:3000",    # Dashboard URL (IP)
    "http://localhost:3001",    # Alternative Dashboard port
    "http://127.0.0.1:3001"     # Alternative Dashboard port (IP)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api.router)
app.include_router(embeddings.router)
app.include_router(auth.router)
app.include_router(google_auth.router, prefix="/api/auth")
app.include_router(twitter.router)  # Thêm Twitter API routes
app.include_router(facebook.router)  # Thêm Facebook API routes

@app.get("/")
async def root():
    return {
        "name": "AI Content Generation Backend",
        "version": "1.0.0",
        "description": "Backend for AI-powered content generation using RAG"
    }

@app.get("/test")
async def test_api():
    """Simple test endpoint to verify API is working properly"""
    from datetime import datetime
    from config.settings import GOOGLE_REDIRECT_URI
    
    return {
        "status": "success",
        "message": "Backend API is working properly",
        "time": datetime.now().isoformat(),
        "google_config": {
            "redirect_uri": GOOGLE_REDIRECT_URI
        }
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"} 