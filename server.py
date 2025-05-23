from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
from app.routes import api, embeddings, auth, google_auth, twitter, facebook

from app.routes import api, embeddings, auth


app = FastAPI(
    title="AI Content Generation Backend",
    description="Backend for AI-powered content generation using RAG with OpenAI, LangChain, and Supabase",
    version="1.0.0"
)


# Enable CORS - cụ thể các origin được phép
origins = [
    "http://localhost:8080",    # Landing page URL
    "http://127.0.0.1:8080",    # Landing page URL (IP)
    "https://localhost:3000",    # Dashboard URL
    "https://127.0.0.1:3000",    # Dashboard URL (IP)
    "http://localhost:3001",    # Alternative Dashboard port
    "http://127.0.0.1:3001",
    "https://api.flowa.one",
    "https://flowa.one",
    "https://ai.flowa.one",         # Alternative Dashboard port (IP)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Use the specific origins list
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],  # Allow all headers
    expose_headers=["*"],  # Expose all headers
    max_age=600  # Cache preflight requests for 10 minutes
)

if __name__ == "__main__":
    # Get port from environment variable or use default
    port = int(os.getenv("PORT", "8009"))
    
    # Run the FastAPI application with uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    ) 