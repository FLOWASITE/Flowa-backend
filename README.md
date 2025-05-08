# AI Content Generation Backend

A Python-based backend for AI-powered content generation using Retrieval Augmented Generation (RAG) with OpenAI, LangChain, and Supabase PostgreSQL.

## Features

- Generate topics based on product information using AI
- Create high-quality content based on topics
- Utilizes RAG (Retrieval Augmented Generation) for better content generation
- Stores and retrieves data using Supabase PostgreSQL
- Uses embeddings for semantic search and similarity matching
- RESTful API endpoints for all operations

## Tech Stack

- **Python**: Core programming language
- **FastAPI**: Web framework for building APIs
- **OpenAI**: Large language model provider for content generation
- **LangChain**: Framework for building LLM applications
- **Supabase**: PostgreSQL database with built-in vector search
- **PostgreSQL**: Database for storing generated content and embeddings

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/ai-content-generation.git
   cd ai-content-generation
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the root directory with the following variables:
   ```
   # OpenAI API Key
   OPENAI_API_KEY=your_openai_api_key

   # Supabase Configuration
   SUPABASE_URL=your_supabase_url
   SUPABASE_KEY=your_supabase_key

   # Database Connection
   DB_HOST=your_supabase_db_host
   DB_NAME=your_supabase_db_name
   DB_USER=your_supabase_db_user
   DB_PASSWORD=your_supabase_db_password
   DB_PORT=5432

   # Application Settings
   MODEL_NAME=gpt-4-turbo
   EMBEDDING_MODEL=text-embedding-ada-002
   EMBEDDING_DIMENSION=1536
   ```

## Database Setup

1. Create the necessary tables in your Supabase PostgreSQL database:

```sql
-- Products table
CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    description TEXT,
    features JSONB,
    embedding VECTOR(1536),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Topics table
CREATE TABLE topics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    product_id UUID REFERENCES products(id),
    prompt TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Content table
CREATE TABLE content (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    topic_id UUID REFERENCES topics(id),
    embedding VECTOR(1536),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

2. Create vector search functions in PostgreSQL:

```sql
-- Function to match documents by embedding similarity
CREATE OR REPLACE FUNCTION match_documents(
    query_embedding VECTOR(1536),
    match_threshold FLOAT,
    match_count INT
)
RETURNS TABLE (
    id UUID,
    content TEXT,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        content.id,
        content.content,
        1 - (content.embedding <=> query_embedding) AS similarity
    FROM content
    WHERE 1 - (content.embedding <=> query_embedding) > match_threshold
    ORDER BY similarity DESC
    LIMIT match_count;
END;
$$;
```

## Usage

1. Start the server:
   ```
   python server.py
   ```

2. The API will be available at `http://localhost:8000`

## API Endpoints

### Content Generation

- `POST /api/topics/generate`: Generate a topic based on product information
- `POST /api/content/generate`: Generate content based on a topic
- `GET /api/topics`: Get a list of generated topics
- `GET /api/content`: Get content by ID or topic ID

### Embeddings Management

- `POST /api/embeddings/products/{product_id}`: Generate embedding for a specific product
- `POST /api/embeddings/products`: Generate embeddings for all products without embeddings

## Development

- The application is structured using a modular approach with controllers, services, and utilities
- Use the FastAPI interactive docs at `http://localhost:8000/docs` for API exploration and testing
- Built-in automatic reloading for development (enabled by default)

## License

MIT 