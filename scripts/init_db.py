from app.utils.database import get_db_connection
import uuid

def init_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Enable UUID extension
    cursor.execute("""
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    """)
    
    # Create products table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        name TEXT NOT NULL,
        description TEXT,
        features JSONB,
        embedding VECTOR(1536),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """)
    
    # Create topics table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS topics (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        title TEXT NOT NULL,
        product_id UUID REFERENCES products(id),
        prompt TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """)
    
    # Create content table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS content (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        topic_id UUID REFERENCES topics(id),
        embedding VECTOR(1536),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """)
    
    # Insert sample product
    product_id = str(uuid.uuid4())
    cursor.execute("""
    INSERT INTO products (id, name, description, features)
    VALUES (%s, %s, %s, %s)
    ON CONFLICT DO NOTHING
    """, (
        product_id,
        'Sữa tươi Vinamilk',
        'Sữa tươi Vinamilk có chứa DHA và Omega 3, giàu canxi và vitamin D, phù hợp cho trẻ em và người lớn',
        '["DHA và Omega 3", "Giàu canxi", "Vitamin D", "Phù hợp mọi lứa tuổi"]'
    ))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print("Database initialized successfully!")
    print(f"Sample product ID: {product_id}")

if __name__ == "__main__":
    init_database() 