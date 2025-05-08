-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create tables if not exists
CREATE TABLE IF NOT EXISTS brands (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    description TEXT,
    features JSONB,
    embedding VECTOR(1536),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS topics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    product_id UUID REFERENCES products(id),
    prompt TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS content (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    topic_id UUID REFERENCES topics(id),
    embedding VECTOR(1536),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert sample brand
INSERT INTO brands (name, description)
VALUES (
    'Vinamilk',
    'Công ty cổ phần sữa Việt Nam, thương hiệu hàng đầu về các sản phẩm sữa và dinh dưỡng'
);

-- Insert sample products
INSERT INTO products (name, description, features)
VALUES 
(
    'Sữa tươi Vinamilk 100% Organic',
    'Sữa tươi organic 100% từ trang trại organic đạt chuẩn châu Âu, giàu dinh dưỡng tự nhiên',
    '["Organic 100%", "Giàu canxi và vitamin D", "Không có hormone tăng trưởng", "Đạt chuẩn organic Châu Âu"]'::jsonb
),
(
    'Sữa tươi Vinamilk Green Farm',
    'Sữa tươi từ trang trại sinh thái Green Farm, bổ sung DHA và Omega 3',
    '["DHA và Omega 3", "Vitamin A & D3", "Protein cao", "Từ trang trại sinh thái"]'::jsonb
);

-- Insert sample topics for each product
WITH product_ids AS (SELECT id FROM products)
INSERT INTO topics (title, product_id, prompt)
SELECT 
    title,
    product_id,
    prompt
FROM (
    SELECT 
        p.id as product_id,
        p.name as product_name,
        unnest(ARRAY[
            'Top 5 lợi ích sức khỏe từ ' || p.name,
            'Hướng dẫn sử dụng ' || p.name || ' hiệu quả nhất',
            'So sánh ' || p.name || ' với các sản phẩm cùng loại'
        ]) as title,
        unnest(ARRAY[
            'Tạo bài viết về lợi ích sức khỏe',
            'Tạo bài viết hướng dẫn sử dụng',
            'Tạo bài viết so sánh sản phẩm'
        ]) as prompt
    FROM products p
) t;

-- Insert sample users
INSERT INTO users (id, email, password_hash, full_name, role) VALUES
('11111111-1111-1111-1111-111111111111', 'admin@flowa.ai', '$2a$12$1234567890123456789012', 'Admin User', 'admin'),
('22222222-2222-2222-2222-222222222222', 'editor@flowa.ai', '$2a$12$1234567890123456789012', 'Editor User', 'editor'),
('33333333-3333-3333-3333-333333333333', 'viewer@flowa.ai', '$2a$12$1234567890123456789012', 'Viewer User', 'viewer');

-- Insert sample profiles
INSERT INTO profiles (user_id, avatar_url, bio, social_links, preferences) VALUES
('11111111-1111-1111-1111-111111111111', 'https://example.com/avatar1.jpg', 'Admin của Flowa AI', 
    '{"linkedin": "https://linkedin.com/admin", "twitter": "https://twitter.com/admin"}'::jsonb,
    '{"theme": "dark", "language": "vi"}'::jsonb);

-- Insert sample brands
INSERT INTO brands (id, name, description, logo_url, website, industry, user_id) VALUES
('44444444-4444-4444-4444-444444444444', 'Vinamilk', 'Công ty cổ phần sữa Việt Nam', 
    'https://example.com/vinamilk-logo.png', 'https://www.vinamilk.com.vn', 'Food & Beverage',
    '11111111-1111-1111-1111-111111111111'),
('55555555-5555-5555-5555-555555555555', 'TH True Milk', 'Công ty cổ phần thực phẩm TH', 
    'https://example.com/th-logo.png', 'https://www.thmilk.vn', 'Food & Beverage',
    '11111111-1111-1111-1111-111111111111');

-- Insert sample brand knowledge
INSERT INTO brand_knowledge (brand_id, title, content, knowledge_type) VALUES
('44444444-4444-4444-4444-444444444444', 'Lịch sử Vinamilk', 'Vinamilk được thành lập từ năm 1976...', 'history'),
('44444444-4444-4444-4444-444444444444', 'Quy trình sản xuất', 'Quy trình sản xuất đạt chuẩn quốc tế...', 'process'),
('55555555-5555-5555-5555-555555555555', 'Trang trại TH', 'Trang trại TH True Milk đạt chuẩn Global GAP...', 'facility');

-- Insert sample products
INSERT INTO products (id, brand_id, name, description, price, features, category, tags) VALUES
('66666666-6666-6666-6666-666666666666', '44444444-4444-4444-4444-444444444444', 
    'Sữa tươi Vinamilk 100% Organic', 'Sữa tươi organic từ trang trại đạt chuẩn châu Âu', 
    45000, 
    '["Organic 100%", "Giàu canxi", "Vitamin D3"]'::jsonb,
    'Sữa tươi',
    ARRAY['organic', 'healthy', 'premium']),
('77777777-7777-7777-7777-777777777777', '55555555-5555-5555-5555-555555555555',
    'Sữa tươi TH True Milk', 'Sữa tươi từ trang trại TH', 
    42000,
    '["Tươi nguyên chất", "Giàu dinh dưỡng"]'::jsonb,
    'Sữa tươi',
    ARRAY['fresh', 'natural']);

-- Insert sample topics
INSERT INTO topics (id, title, description, brand_id, product_id, user_id, category, status, keywords, relevance_score, target_audience) VALUES
('88888888-8888-8888-8888-888888888888',
    'Top 5 lợi ích của sữa organic với sức khỏe',
    'Bài viết về lợi ích của sữa organic',
    '44444444-4444-4444-4444-444444444444',
    '66666666-6666-6666-6666-666666666666',
    '22222222-2222-2222-2222-222222222222',
    'health',
    'published',
    '["sữa organic", "sức khỏe", "dinh dưỡng"]'::jsonb,
    95,
    'Phụ huynh quan tâm đến sức khỏe gia đình'
);

-- Insert sample content
INSERT INTO content (id, title, content, topic_id, user_id, format, status, seo_title, seo_description, word_count, reading_time) VALUES
('99999999-9999-9999-9999-999999999999',
    'Top 5 lợi ích tuyệt vời của sữa organic đối với sức khỏe',
    '# Top 5 lợi ích của sữa organic\n\n1. Giàu dưỡng chất tự nhiên\n2. Không có hormone tăng trưởng\n3. Tốt cho hệ miễn dịch\n4. An toàn cho trẻ em\n5. Thân thiện với môi trường',
    '88888888-8888-8888-8888-888888888888',
    '22222222-2222-2222-2222-222222222222',
    'markdown',
    'published',
    'Top 5 lợi ích của sữa organic - Vinamilk',
    'Khám phá 5 lợi ích tuyệt vời của sữa organic đối với sức khỏe của bạn và gia đình',
    500,
    3
);

-- Insert sample platforms
INSERT INTO platforms (name, api_endpoint, description) VALUES
('Facebook', 'https://graph.facebook.com/v13.0', 'Facebook Marketing API'),
('Instagram', 'https://graph.instagram.com/v13.0', 'Instagram API'),
('TikTok', 'https://open.tiktokapis.com/v2', 'TikTok Marketing API');

-- Insert sample social accounts
INSERT INTO social_accounts (platform_id, brand_id, account_name, account_type, status) 
SELECT 
    p.id as platform_id,
    '44444444-4444-4444-4444-444444444444' as brand_id,
    'vinamilk_official' as account_name,
    'business' as account_type,
    'active' as status
FROM platforms p
WHERE p.name = 'Facebook';

-- Insert sample scheduling preferences
INSERT INTO scheduling_preferences (brand_id, platform_id, preferred_times, frequency)
SELECT 
    '44444444-4444-4444-4444-444444444444' as brand_id,
    p.id as platform_id,
    '{"monday": ["09:00", "15:00"], "wednesday": ["10:00", "16:00"], "friday": ["11:00", "17:00"]}'::jsonb as preferred_times,
    'weekly' as frequency
FROM platforms p
WHERE p.name = 'Facebook';

-- Insert sample CRM contacts
INSERT INTO crm_contacts (brand_id, first_name, last_name, email, phone, social_profiles, tags) VALUES
('44444444-4444-4444-4444-444444444444', 'Nguyễn', 'Văn A', 'nguyenvana@email.com', '0901234567',
    '{"facebook": "fb.com/nguyenvana", "instagram": "instagram.com/nguyenvana"}'::jsonb,
    ARRAY['potential', 'interested']);

-- Insert sample QA pairs
INSERT INTO qa_pairs (brand_id, question, answer, category, tags) VALUES
('44444444-4444-4444-4444-444444444444',
    'Sữa organic có những lợi ích gì?',
    'Sữa organic có nhiều lợi ích như: giàu dưỡng chất tự nhiên, không có hormone tăng trưởng, tốt cho hệ miễn dịch...',
    'product',
    ARRAY['organic', 'health', 'benefits']); 