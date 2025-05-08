from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.routes import api, embeddings

app = FastAPI(
    title="AI Content Generation Backend",
    description="Backend for AI-powered content generation using RAG with OpenAI, LangChain, and Supabase",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update with appropriate origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api.router)
app.include_router(embeddings.router)

@app.get("/")
async def root():
    return {
        "name": "AI Content Generation Backend",
        "version": "1.0.0",
        "description": "Backend for AI-powered content generation using RAG"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"} 