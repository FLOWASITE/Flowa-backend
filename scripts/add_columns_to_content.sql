-- Script để thêm các cột mới vào bảng content
-- Thêm cột embedding để lưu trữ vector embedding
ALTER TABLE content ADD COLUMN IF NOT EXISTS embedding vector;

-- Thêm cột preview_image để lưu trữ ảnh dưới dạng base64
ALTER TABLE content ADD COLUMN IF NOT EXISTS preview_image text;

-- Thêm cột seo_title để lưu trữ tiêu đề SEO
ALTER TABLE content ADD COLUMN IF NOT EXISTS seo_title varchar(255);

-- Thêm cột seo_description để lưu trữ mô tả SEO
ALTER TABLE content ADD COLUMN IF NOT EXISTS seo_description text;

-- Thêm cột word_count để lưu trữ số từ trong nội dung
ALTER TABLE content ADD COLUMN IF NOT EXISTS word_count integer;

-- Tạo index cho cột embedding để tăng tốc độ tìm kiếm
CREATE INDEX IF NOT EXISTS content_embedding_idx ON content USING ivfflat (embedding vector_cosine_ops);

-- Thông báo hoàn thành
SELECT 'Đã thêm các cột mới vào bảng content' as message;
