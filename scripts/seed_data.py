from app.utils.database import get_db_connection
import uuid
import json

def seed_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Insert sample brands
        brand_id = str(uuid.uuid4())
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS brands (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            name TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """)
        
        cursor.execute("""
        INSERT INTO brands (id, name, description)
        VALUES (%s, %s, %s)
        RETURNING id;
        """, (
            brand_id,
            'Vinamilk',
            'Công ty cổ phần sữa Việt Nam, thương hiệu hàng đầu về các sản phẩm sữa và dinh dưỡng'
        ))
        
        # Insert sample products
        products_data = [
            {
                'name': 'Sữa tươi Vinamilk 100% Organic',
                'description': 'Sữa tươi organic 100% từ trang trại organic đạt chuẩn châu Âu, giàu dinh dưỡng tự nhiên',
                'features': json.dumps([
                    'Organic 100%',
                    'Giàu canxi và vitamin D',
                    'Không có hormone tăng trưởng',
                    'Đạt chuẩn organic Châu Âu'
                ])
            },
            {
                'name': 'Sữa tươi Vinamilk Green Farm',
                'description': 'Sữa tươi từ trang trại sinh thái Green Farm, bổ sung DHA và Omega 3',
                'features': json.dumps([
                    'DHA và Omega 3',
                    'Vitamin A & D3',
                    'Protein cao',
                    'Từ trang trại sinh thái'
                ])
            }
        ]
        
        for product in products_data:
            product_id = str(uuid.uuid4())
            cursor.execute("""
            INSERT INTO products (id, name, description, features)
            VALUES (%s, %s, %s, %s)
            RETURNING id;
            """, (
                product_id,
                product['name'],
                product['description'],
                product['features']
            ))
            
            # Insert sample topics for each product
            topics_data = [
                {
                    'title': f'Top 5 lợi ích sức khỏe từ {product["name"]}',
                    'prompt': 'Tạo bài viết về lợi ích sức khỏe'
                },
                {
                    'title': f'Hướng dẫn sử dụng {product["name"]} hiệu quả nhất',
                    'prompt': 'Tạo bài viết hướng dẫn sử dụng'
                },
                {
                    'title': f'So sánh {product["name"]} với các sản phẩm cùng loại',
                    'prompt': 'Tạo bài viết so sánh sản phẩm'
                }
            ]
            
            for topic in topics_data:
                topic_id = str(uuid.uuid4())
                cursor.execute("""
                INSERT INTO topics (id, title, product_id, prompt)
                VALUES (%s, %s, %s, %s)
                RETURNING id;
                """, (
                    topic_id,
                    topic['title'],
                    product_id,
                    topic['prompt']
                ))
                
                # Insert sample content for each topic
                cursor.execute("""
                INSERT INTO content (title, content, topic_id)
                VALUES (%s, %s, %s)
                RETURNING id;
                """, (
                    topic['title'],
                    f'Nội dung mẫu cho chủ đề: {topic["title"]}. Sẽ được tạo tự động bởi AI.',
                    topic_id
                ))
        
        conn.commit()
        print("Sample data inserted successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    seed_database() 