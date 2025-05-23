from app.services.rag_service import RAGService
from app.utils.database import fetch_data, get_db_connection
from langchain.prompts import PromptTemplate
import json

class ContentController:
    def __init__(self):
        self.rag_service = RAGService()
    
    async def generate_topic(self, product_id=None, product_query=None, brand_id=None, prompt=None, count=1, use_previous_topics=True, max_previous_topics=5):
        """
        Generate multiple topics based on product information, brand info and previous topics.
        
        Args:
            product_id (str, optional): ID of a specific product
            product_query (str, optional): Query to find relevant products
            brand_id (str, optional): ID of the brand
            prompt (str, optional): Additional prompt instructions
            count (int): Number of topics to generate (default: 1)
            use_previous_topics (bool): Whether to use previous topics as context
            max_previous_topics (int): Maximum number of previous topics to use
            
        Returns:
            dict: Generated topics
        """
        try:
            # Get product context
            product_context = ""
            brand_info = ""
            previous_topics = []
            
            if product_id:
                # Fetch specific product from database
                products = fetch_data("products", f"id = '{product_id}'")
                if products:
                    product = products[0]
                    product_context = f"Tên sản phẩm: {product.get('name', '')}\nMô tả: {product.get('description', '')}"
                    
                    # Get features if available
                    if product.get('features'):
                        features = product.get('features')
                        if isinstance(features, str):
                            try:
                                features = json.loads(features)
                            except:
                                pass
                        if isinstance(features, list):
                            product_context += "\nTính năng:\n"
                            for feature in features:
                                product_context += f"- {feature}\n"
                    
                    # Get brand info if brand_id is provided
                    if brand_id:
                        brands = fetch_data("brands", f"id = '{brand_id}'")
                        if brands:
                            brand = brands[0]
                            brand_info = f"Thông tin thương hiệu:\nTên: {brand.get('name', '')}\nMô tả: {brand.get('description', '')}"
                    
                    # Get previous topics if requested
                    if use_previous_topics:
                        # Get topics for this product
                        product_topics = fetch_data("topics", f"product_id = '{product_id}'", limit=max_previous_topics)
                        if product_topics:
                            previous_topics.extend([topic.get('title') for topic in product_topics])
                        
                        # If brand_id is provided, get topics for other products of the same brand
                        if brand_id:
                            brand_topics = fetch_data(
                                "topics",
                                f"product_id IN (SELECT id FROM products WHERE brand_id = '{brand_id}') AND product_id != '{product_id}'",
                                limit=max_previous_topics
                            )
                            if brand_topics:
                                previous_topics.extend([topic.get('title') for topic in brand_topics])
            
            elif product_query:
                # Retrieve relevant products based on query
                products = self.rag_service.retrieve_relevant_products(product_query)
                product_context = "\n\n".join(products)
            
            if not product_context:
                raise ValueError("Không tìm thấy thông tin sản phẩm.")
            
            # If count > 1, use the same approach as generate_brand_product_topics
            if count > 1:
                # Generate topics with enhanced template
                topics_template = """
                Bạn là một chuyên gia sáng tạo nội dung và tiếp thị.
                
                Dựa trên thông tin sau đây, hãy tạo ra {count} chủ đề hấp dẫn và thân thiện với SEO:
                
                Thông tin sản phẩm:
                {product_info}
                
                {brand_context}
                
                {previous_topics_context}
                
                {prompt_context}
                
                Tạo ra các chủ đề và phân loại chúng vào một trong các nhóm sau:
                - Product Updates: Cập nhật về sản phẩm
                - Industry News: Tin tức ngành
                - Customer Stories: Câu chuyện khách hàng
                - Tips & Tricks: Mẹo và thủ thuật
                - Behind the Scenes: Hậu trường
                - Company Culture: Văn hóa công ty
                - Educational Content: Nội dung giáo dục
                - Product Features: Tính năng sản phẩm
                
                Tạo ra các chủ đề mà:
                1. Liên quan đến sản phẩm và phù hợp với định vị thương hiệu
                2. Có khả năng thu hút khách hàng tiềm năng
                3. Mang lại giá trị cho người đọc
                4. Được tối ưu hóa cho công cụ tìm kiếm
                5. Phù hợp cho tiếp thị nội dung
                6. KHÔNG trùng lặp với các chủ đề đã có (nếu có)
                7. Có tính độc đáo và sáng tạo
                
                Trả về kết quả dưới dạng JSON với định dạng sau:
                {{
                    "topics": [
                        {{
                            "title": "Tiêu đề chủ đề",
                            "relevance_score": số từ 0-100 đánh giá độ liên quan,
                            "seo_keywords": ["từ khóa 1", "từ khóa 2", "từ khóa 3"],
                            "target_audience": "Mô tả đối tượng mục tiêu",
                            "category": "Tên phân loại (một trong các loại đã liệt kê ở trên)"
                        }},
                        ...
                    ]
                }}
                
                Chỉ trả về JSON, không thêm giải thích hoặc bình luận nào khác.
                """
                
                # Prepare context
                brand_context = "Thông tin thương hiệu:\n" + brand_info if brand_info else ""
                
                previous_topics_context = ""
                if previous_topics and len(previous_topics) > 0:
                    previous_topics_context = "Các chủ đề đã có:\n" + "\n".join([f"- {topic}" for topic in previous_topics])
                else:
                    previous_topics_context = "Không có chủ đề đã tạo trước đây."
                    
                prompt_context = f"Yêu cầu bổ sung:\n{prompt}" if prompt else "Không có yêu cầu bổ sung."
                
                # Create and format prompt
                topics_prompt = PromptTemplate(
                    template=topics_template,
                    input_variables=["count", "product_info", "brand_context", "previous_topics_context", "prompt_context"]
                )
                
                formatted_prompt = topics_prompt.format(
                    count=count,
                    product_info=product_context,
                    brand_context=brand_context,
                    previous_topics_context=previous_topics_context,
                    prompt_context=prompt_context
                )
                
                # Generate topics
                response = self.rag_service.openai.invoke(formatted_prompt)
                
                # Parse response
                try:
                    result = json.loads(response.content)
                except json.JSONDecodeError:
                    # Fallback: If response isn't valid JSON, try to extract JSON
                    content = response.content
                    start_idx = content.find('{')
                    end_idx = content.rfind('}') + 1
                    
                    if start_idx >= 0 and end_idx > start_idx:
                        json_content = content[start_idx:end_idx]
                        try:
                            result = json.loads(json_content)
                        except:
                            return {
                                "success": False,
                                "error": "Không thể định dạng phản hồi thành JSON",
                                "raw_content": content
                            }
                    else:
                        return {
                            "success": False,
                            "error": "Không thể định dạng phản hồi thành JSON",
                            "raw_content": content
                        }
                
                # Add metadata but don't save to database yet
                topics = []
                for topic_data in result.get("topics", []):
                    # Add product_id and brand_id to each topic
                    topic_data["product_id"] = product_id
                    topic_data["brand_id"] = brand_id
                    topic_data["prompt"] = prompt
                    topic_data["status"] = "draft"  # Default status is draft
                    topics.append(topic_data)
                
                return {
                    "success": True,
                    "topics": topics
                }
            else:
                # Original logic for single topic
                topic = self.rag_service.generate_topic_from_context(
                    product_context=product_context,
                    brand_info=brand_info if brand_info else None,
                    previous_topics=previous_topics if previous_topics else None,
                    prompt=prompt
                )
                
                # Return topic without saving to database
                return {
                    "success": True,
                    "topic": {
                        "title": topic,
                        "product_id": product_id,
                        "brand_id": brand_id,
                        "prompt": prompt,
                        "status": "draft"  # Default status is draft
                    }
                }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def generate_brand_product_topics(self, brand_id, product_id, count=3, save_to_db=False, prompt=None, use_previous_topics=False, max_previous_topics=5):
        """
        Generate multiple topics for a product from a specific brand.
        
        Args:
            brand_id (str): ID of the brand
            product_id (str): ID of the product to base topics on
            count (int): Number of topics to generate
            save_to_db (bool): Whether to save generated topics to database
            prompt (str, optional): Additional prompt instructions
            use_previous_topics (bool): Whether to use previous topics as context
            max_previous_topics (int): Maximum number of previous topics to use
            
        Returns:
            dict: Generated topics in JSON format
        """
        try:
            # Fetch product information
            product_data = fetch_data("products", f"id = '{product_id}'")
            if not product_data:
                return {
                    "success": False,
                    "error": "Không tìm thấy sản phẩm"
                }
            
            product = product_data[0]
            product_context = f"Tên sản phẩm: {product.get('name', '')}\nMô tả: {product.get('description', '')}"
            
            if product.get('features'):
                features = product.get('features')
                if isinstance(features, str):
                    try:
                        features = json.loads(features)
                    except:
                        pass
                
                if isinstance(features, list):
                    product_context += "\nTính năng:\n"
                    for feature in features:
                        product_context += f"- {feature}\n"
            
            # Fetch brand information
            brand_info = ""
            brands = fetch_data("brands", f"id = '{brand_id}'")
            if brands:
                brand = brands[0]
                brand_info = f"Thông tin thương hiệu:\nTên: {brand.get('name', '')}\nMô tả: {brand.get('description', '')}"
            
            # Get previous topics if requested
            previous_topics = []
            if use_previous_topics:
                # Get topics for this product
                product_topics = fetch_data("topics", f"product_id = '{product_id}'", limit=max_previous_topics)
                if product_topics:
                    previous_topics.extend([topic.get('title') for topic in product_topics])
                
                # Get topics for other products of the same brand
                brand_topics = fetch_data(
                    "topics",
                    f"product_id IN (SELECT id FROM products WHERE brand_id = '{brand_id}') AND product_id != '{product_id}'",
                    limit=max_previous_topics
                )
                if brand_topics:
                    previous_topics.extend([topic.get('title') for topic in brand_topics])
            
            # Generate topics with enhanced template
            topics_template = """
            Bạn là một chuyên gia sáng tạo nội dung và tiếp thị.
            
            Dựa trên thông tin sau đây, hãy tạo ra {count} chủ đề hấp dẫn và thân thiện với SEO:
            
            Thông tin sản phẩm:
            {product_info}
            
            {brand_context}
            
            {previous_topics_context}
            
            {prompt_context}
            
            Tạo ra các chủ đề và phân loại chúng vào một trong các nhóm sau:
            - Product Updates: Cập nhật về sản phẩm
            - Industry News: Tin tức ngành
            - Customer Stories: Câu chuyện khách hàng
            - Tips & Tricks: Mẹo và thủ thuật
            - Behind the Scenes: Hậu trường
            - Company Culture: Văn hóa công ty
            - Educational Content: Nội dung giáo dục
            - Product Features: Tính năng sản phẩm
            
            Tạo ra các chủ đề mà:
            1. Liên quan đến sản phẩm và phù hợp với định vị thương hiệu
            2. Có khả năng thu hút khách hàng tiềm năng
            3. Mang lại giá trị cho người đọc
            4. Được tối ưu hóa cho công cụ tìm kiếm
            5. Phù hợp cho tiếp thị nội dung
            6. KHÔNG trùng lặp với các chủ đề đã có (nếu có)
            7. Có tính độc đáo và sáng tạo
            
            Trả về kết quả dưới dạng JSON với định dạng sau:
            {{
                "topics": [
                    {{
                        "title": "Tiêu đề chủ đề",
                        "relevance_score": số từ 0-100 đánh giá độ liên quan,
                        "seo_keywords": ["từ khóa 1", "từ khóa 2", "từ khóa 3"],
                        "target_audience": "Mô tả đối tượng mục tiêu",
                        "category": "Tên phân loại (một trong các loại đã liệt kê ở trên)"
                    }},
                    ...
                ]
            }}
            
            Chỉ trả về JSON, không thêm giải thích hoặc bình luận nào khác.
            """
            
            # Prepare context
            brand_context = brand_info if brand_info else "Không có thông tin về thương hiệu."
            
            previous_topics_context = ""
            if previous_topics and len(previous_topics) > 0:
                previous_topics_context = "Các chủ đề đã có:\n" + "\n".join([f"- {topic}" for topic in previous_topics])
            else:
                previous_topics_context = "Không có chủ đề đã tạo trước đây."
                
            prompt_context = f"Yêu cầu bổ sung:\n{prompt}" if prompt else "Không có yêu cầu bổ sung."
            
            # Create and format prompt
            topics_prompt = PromptTemplate(
                template=topics_template,
                input_variables=["count", "product_info", "brand_context", "previous_topics_context", "prompt_context"]
            )
            
            formatted_prompt = topics_prompt.format(
                count=count,
                product_info=product_context,
                brand_context=brand_context,
                previous_topics_context=previous_topics_context,
                prompt_context=prompt_context
            )
            
            # Generate topics
            response = self.rag_service.openai.invoke(formatted_prompt)
            
            # Parse response
            try:
                result = json.loads(response.content)
            except json.JSONDecodeError:
                # Fallback: If response isn't valid JSON, try to extract JSON
                content = response.content
                start_idx = content.find('{')
                end_idx = content.rfind('}') + 1
                
                if start_idx >= 0 and end_idx > start_idx:
                    json_content = content[start_idx:end_idx]
                    try:
                        result = json.loads(json_content)
                    except:
                        return {
                            "success": False,
                            "error": "Không thể định dạng phản hồi thành JSON",
                            "raw_content": content
                        }
                else:
                    return {
                        "success": False,
                        "error": "Không thể định dạng phản hồi thành JSON",
                        "raw_content": content
                    }
            
            # Add metadata but don't save to database by default
            topics = []
            for topic_data in result.get("topics", []):
                # Add product_id and brand_id to each topic
                topic_data["product_id"] = product_id
                topic_data["brand_id"] = brand_id
                topic_data["prompt"] = prompt
                topic_data["status"] = "draft"  # Default status is draft
                topics.append(topic_data)
            
            # Optionally save topics to database
            if save_to_db:
                saved_topics = await self.save_approved_topics(topics)
                return saved_topics
            
            return {
                "success": True,
                "topics": topics
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def save_approved_topics(self, topics, save_to_db=True):
        """
        Save approved topics to database.
        
        Args:
            topics (list): List of topics to save
            save_to_db (bool): Whether to actually save to database
            
        Returns:
            dict: Saved topics
        """
        try:
            if not save_to_db:
                return {
                    "success": True,
                    "topics": topics
                }
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            saved_topics = []
            
            for topic_data in topics:
                # Only save topics with status 'complete'
                if topic_data.get("status") != "complete":
                    continue
                
                # Create a new topic record
                query = """
                INSERT INTO topics (
                    title, 
                    product_id, 
                    brand_id, 
                    keywords, 
                    relevance_score, 
                    target_audience, 
                    prompt, 
                    category,
                    status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, title, created_at, category, status
                """
                
                cursor.execute(query, (
                    topic_data.get("title", ""),
                    topic_data.get("product_id"),
                    topic_data.get("brand_id"),
                    json.dumps(topic_data.get("seo_keywords", [])),
                    topic_data.get("relevance_score", 0),
                    topic_data.get("target_audience", ""),
                    topic_data.get("prompt", ""),
                    topic_data.get("category", ""),
                    "published"  # Set status to published when saving to database
                ))
                db_result = cursor.fetchone()
                
                # Add all data to result
                result_topic = {
                    "id": db_result["id"],
                    "title": db_result["title"],
                    "created_at": db_result["created_at"],
                    "category": db_result["category"],
                    "status": db_result["status"],
                    **{k: v for k, v in topic_data.items() if k not in ["id", "created_at"]}
                }
                
                saved_topics.append(result_topic)
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return {
                "success": True,
                "topics": saved_topics
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def generate_content(self, topic_id=None, topic_title=None, with_related=True):
        """
        Generate content based on a topic.
        
        Args:
            topic_id (str, optional): ID of an existing topic
            topic_title (str, optional): Title of the topic to generate content for
            with_related (bool): Whether to include related content
            
        Returns:
            dict: Generated content
        """
        try:
            topic = topic_title
            
            # If topic_id is provided, fetch the topic from the database
            if topic_id and not topic:
                topics = fetch_data("topics", f"id = '{topic_id}'")
                if topics:
                    topic = topics[0].get("title", "")
            
            if not topic:
                return {
                    "success": False,
                    "error": "Topic not found or not provided"
                }
            
            # Generate content using RAG service
            content = self.rag_service.generate_content_from_topic(
                topic=topic,
                with_related=with_related
            )
            
            # Save content to database
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Create a new content record
            query = """
            INSERT INTO content (title, content, topic_id)
            VALUES (%s, %s, %s)
            RETURNING id, title, created_at
            """
            
            cursor.execute(query, (topic, content, topic_id))
            result = cursor.fetchone()
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return {
                "success": True,
                "content": {
                    "id": result["id"],
                    "title": result["title"],
                    "content": content,
                    "created_at": result["created_at"]
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_topics(self, limit=10):
        """
        Get list of generated topics.
        
        Args:
            limit (int): Maximum number of topics to retrieve
            
        Returns:
            dict: List of topics
        """
        try:
            topics = fetch_data("topics", limit=limit)
            
            return {
                "success": True,
                "topics": topics
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_content(self, content_id=None, topic_id=None, limit=10):
        """
        Get content by ID or topic ID.
        
        Args:
            content_id (str, optional): ID of content to retrieve
            topic_id (str, optional): ID of topic to retrieve content for
            limit (int): Maximum number of content items to retrieve
            
        Returns:
            dict: Content data
        """
        try:
            if content_id:
                content = fetch_data("content", f"id = '{content_id}'")
            elif topic_id:
                content = fetch_data("content", f"topic_id = '{topic_id}'")
            else:
                content = fetch_data("content", limit=limit)
            
            return {
                "success": True,
                "content": content
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def generate_content_from_approved_topic(self, topic_id, with_related=True, save_to_db=True):
        """
        Tạo nội dung cho một chủ đề cụ thể đã được duyệt sử dụng RAG.
        
        Args:
            topic_id (str): ID của chủ đề đã được duyệt
            with_related (bool): Có sử dụng nội dung liên quan làm ngữ cảnh hay không
            save_to_db (bool): Có lưu nội dung đã tạo vào cơ sở dữ liệu hay không
            
        Returns:
            dict: Nội dung đã tạo
        """
        try:
            # Lấy thông tin chủ đề từ cơ sở dữ liệu
            topics = fetch_data("topics", f"id = '{topic_id}'")
            
            if not topics:
                return {
                    "success": False,
                    "error": f"Không tìm thấy chủ đề với ID '{topic_id}'"
                }
            
            topic = topics[0]
            topic_title = topic.get("title")
            
            # Kiểm tra xem nội dung đã tồn tại cho chủ đề này chưa
            existing_content = fetch_data("content", f"topic_id = '{topic_id}'")
            
            # Chuẩn bị ngữ cảnh từ nội dung hiện có (nếu có)
            existing_content_context = None
            if existing_content:
                content_item = existing_content[0]
                existing_content_context = content_item.get("content")
            try:
                # Tạo nội dung mới sử dụng RAG và tối ưu hóa cho mạng xã hội
                related_content = []
                
                # Thêm nội dung hiện có vào ngữ cảnh nếu có
                if existing_content_context:
                    related_content.append(f"Nội dung hiện có cho chủ đề này: {existing_content_context}")
                
                # Thêm nội dung liên quan từ vector store nếu được yêu cầu
                if with_related:
                    try:
                        # Lấy nội dung liên quan cho chủ đề này
                        retrieved_content = self.rag_service.retrieve_related_content(topic_title)
                        if retrieved_content:
                            related_content.extend(retrieved_content)
                    except Exception as e:
                        # Xử lý lỗi khi không thể lấy nội dung liên quan
                        print(f"Lỗi khi lấy nội dung liên quan: {str(e)}")
                        # Thêm thông tin về chủ đề và metadata để bổ sung ngữ cảnh
                        related_content.append(f"Chủ đề: {topic_title}")
                        if topic.get("keywords"):
                            related_content.append(f"Từ khóa: {', '.join(topic.get('keywords', []))}")
                        if topic.get("category"):
                            related_content.append(f"Danh mục: {topic.get('category', '')}")
                        if topic.get("target_audience"):
                            related_content.append(f"Đối tượng mục tiêu: {topic.get('target_audience', '')}")
                        # Thêm thông tin sản phẩm nếu có
                        if topic.get("product_id"):
                            try:
                                product_data = fetch_data("products", f"id = '{topic.get('product_id')}'")
                                if product_data:
                                    product = product_data[0]
                                    related_content.append(f"Sản phẩm: {product.get('name', '')}")
                                    related_content.append(f"Mô tả sản phẩm: {product.get('description', '')}")
                            except Exception as product_error:
                                print(f"Lỗi khi lấy thông tin sản phẩm: {str(product_error)}")
                                pass
            except Exception as e:
                print(f"Lỗi khi chuẩn bị nội dung liên quan: {str(e)}")
                related_content = []
            
            # Tạo nội dung cho mạng xã hội
            social_media_template = """
            Bạn là một chuyên gia sáng tạo nội dung cho mạng xã hội.
            
            Nhiệm vụ: Tạo nội dung hấp dẫn và tối ưu cho mạng xã hội về chủ đề sau:
            Chủ đề: {topic}
            
            Thông tin/ngữ cảnh bổ sung:
            {context}
            
            Hướng dẫn:
            1. Tạo nội dung ngắn gọn, hấp dẫn và dễ chia sẻ
            2. Tối ưu hóa cho các nền tảng mạng xã hội (Facebook, Instagram, LinkedIn, TikTok)
            3. Sử dụng ngôn ngữ cuốn hút và kêu gọi hành động
            4. Đề xuất hashtag phù hợp
            5. Tạo nội dung có tính tương tác cao
            6. Đảm bảo nội dung có giá trị và thông tin chính xác
            7. Sử dụng từ ngữ và cách diễn đạt bằng tiếng Việt tự nhiên, dễ hiểu
            
            Trả về kết quả theo định dạng JSON sau:
            {{"facebook": "Nội dung cho Facebook", "instagram": "Nội dung cho Instagram", "linkedin": "Nội dung cho LinkedIn", "tiktok": "Nội dung cho TikTok", "hashtags": ["hashtag1", "hashtag2", ...]}}
            
            Lưu ý: Điều chỉnh độ dài và phong cách phù hợp với từng nền tảng.
            """
            
            social_media_prompt = PromptTemplate(
                template=social_media_template,
                input_variables=["topic", "context"]
            )
            
            # Chuẩn bị ngữ cảnh - giới hạn độ dài để tránh lỗi token limit
            # Giới hạn số lượng nội dung liên quan
            limited_related_content = related_content[:2] if related_content else []
            
            # Giới hạn độ dài mỗi mục
            limited_related_content = [item[:300] for item in limited_related_content]
            
            context = "\n\n".join([f"- {item}" for item in limited_related_content]) if limited_related_content else "Không có ngữ cảnh bổ sung nào được cung cấp. Hãy tạo nội dung gốc dựa trên chủ đề."
            
            # Tạo nội dung cho mạng xã hội
            formatted_prompt = social_media_prompt.format(topic=topic_title, context=context)
            
            try:
                # Giảm nhiệt độ để giảm sử dụng token và tăng tính ổn định
                original_temp = self.rag_service.openai.temperature
                self.rag_service.openai.temperature = 0.5
                
                try:
                    response = self.rag_service.openai.invoke(formatted_prompt)
                finally:
                    # Khôi phục nhiệt độ ban đầu
                    self.rag_service.openai.temperature = original_temp
            except Exception as e:
                error_message = str(e)
                print(f"Lỗi khi gọi OpenAI API: {error_message}")
                
                # Kiểm tra nếu là lỗi rate limit hoặc quota
                if "rate limit" in error_message.lower() or "quota" in error_message.lower() or "429" in error_message or "insufficient_quota" in error_message.lower():
                    return {
                        "success": False,
                        "error": "Hệ thống đang tạm thời quá tải. Vui lòng thử lại sau ít phút.",
                        "technical_error": error_message
                    }
                
                # Lỗi khác
                return {
                    "success": False,
                    "error": "Lỗi khi tạo nội dung. Vui lòng thử lại.",
                    "technical_error": error_message
                }
            
            try:
                # Phân tích phản hồi JSON
                # Thêm xử lý để tìm và trích xuất JSON từ nội dung
                content_str = response.content
                # Tìm JSON trong nội dung (nếu có ký tự khác ở đầu hoặc cuối)
                json_start = content_str.find('{')
                json_end = content_str.rfind('}')
                
                if json_start >= 0 and json_end > json_start:
                    # Trích xuất phần JSON
                    json_str = content_str[json_start:json_end+1]
                    content = json.loads(json_str)
                else:
                    # Nếu không tìm thấy JSON, sử dụng nội dung gốc
                    raise json.JSONDecodeError("No JSON found", content_str, 0)
            except json.JSONDecodeError:
                # Nếu không phải JSON, sử dụng nội dung gốc
                print(f"Lỗi khi phân tích JSON: {response.content}")
                content = {
                    "error": "Không thể phân tích nội dung JSON",
                    "raw_content": response.content,
                    "facebook": response.content,
                    "instagram": response.content,
                    "linkedin": response.content,
                    "tiktok": response.content,
                    "hashtags": []
                }
            
            # Tạo ảnh liên quan đến nội dung
            # try:    
            #     # Tạo một mô tả tổng hợp từ nội dung mạng xã hội
            #     image_content = f"Chủ đề: {topic_title}\n\nNội dung Facebook: {content.get('facebook', '')}\n\nNội dung Instagram: {content.get('instagram', '')}\n\nHashtags: {', '.join(content.get('hashtags', []))}"
                
            #     # Tạo ảnh từ nội dung
            #     image_data = self.rag_service.generate_image_from_content(image_content)
                
            #     if image_data:
            #         # Thêm thông tin ảnh vào nội dung
            #         content["image"] = {
            #             "description": image_data.get("description", ""),
            #             "base64_data": image_data.get("base64_data", ""),
            #             "format": image_data.get("format", "png")
            #         }
            #         content["preview_image"] = f"data:image/{image_data.get('format', 'png')};base64,{image_data.get('base64_data', '')}"
            #         content["seo_title"] = topic_title
            #         content["seo_description"] = content.get('facebook', '')[:160] if content.get('facebook') else topic_title
            #         content["word_count"] = len(' '.join([content.get('facebook', ''), content.get('instagram', ''), content.get('linkedin', ''), content.get('tiktok', '')]))
            # except Exception as e:
            #     print(f"Lỗi khi tạo ảnh: {str(e)}")
            #     # Vẫn tiếp tục mà không có ảnh
            
            # Tạo embedding vector cho nội dung
            try:
                # Kết hợp tất cả nội dung để tạo embedding
                # Giới hạn độ dài văn bản để tránh lỗi token limit
                facebook_content = content.get('facebook', '')[:300] if content.get('facebook') else ''
                instagram_content = content.get('instagram', '')[:300] if content.get('instagram') else ''
                
                # embedding_text = f"Chủ đề: {topic_title}\n\nNội dung: {facebook_content} {instagram_content}"
                
                # # Tạo embedding vector
                # embedding_vector = self.rag_service.embedding_service.generate_embedding(embedding_text)
                
                # # Thêm embedding vector vào nội dung (chỉ để tham khảo)
                # content["embedding"] = embedding_vector
            except Exception as e:
                print(f"Lỗi khi tạo embedding: {str(e)}")
                # Vẫn tiếp tục mà không có embedding
                # embedding_vector = None
            
            # Chuyển đổi nội dung JSON thành chuỗi để lưu trữ
            content_json = json.dumps(content, ensure_ascii=False)
            
            if save_to_db:
                # Lưu nội dung vào cơ sở dữ liệu
                conn = get_db_connection()
                cursor = conn.cursor()
                
                # Kiểm tra cấu trúc bảng content để xác định các cột hiện có
                try:
                    # Thử truy vấn cấu trúc bảng
                    cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'content'")
                    columns = [col[0] for col in cursor.fetchall()]
                    has_metadata_column = 'metadata' in columns
                    has_embedding_column = 'embedding' in columns
                    has_preview_image_column = 'preview_image' in columns
                    has_seo_title_column = 'seo_title' in columns
                    has_seo_description_column = 'seo_description' in columns
                    has_word_count_column = 'word_count' in columns
                    
                    # Chuẩn bị các cột và giá trị để chèn
                    insert_columns = ["title", "content", "topic_id"]
                    insert_values = [topic_title, content_json, topic_id]
                    
                    # Thêm metadata nếu có cột
                    if has_metadata_column:
                        insert_columns.append("metadata")
                        metadata = {
                            "generated_with_related": with_related,
                            "topic_status": topic.get("status", ""),
                            "topic_category": topic.get("category", ""),
                            "topic_keywords": topic.get("keywords", []),
                            "content_type": "social_media",
                            "platforms": ["facebook", "instagram", "linkedin", "tiktok"],
                            "has_existing_content": existing_content_context is not None
                        }
                        insert_values.append(json.dumps(metadata))
                    
                    # Thêm embedding nếu có cột và đã tạo embedding
                    if has_embedding_column and embedding_vector is not None:
                        insert_columns.append("embedding")
                        # Định dạng embedding vector cho PostgreSQL
                        # PostgreSQL yêu cầu vector được định dạng dưới dạng cụ thể
                        # Chú ý: Sử dụng cú pháp đặc biệt của PostgreSQL cho kiểu dữ liệu vector
                        formatted_vector = f"[{','.join(str(x) for x in embedding_vector)}]"
                        insert_values.append(formatted_vector)
                    
                    # Thêm preview_image nếu có cột và đã tạo ảnh
                    if has_preview_image_column and "preview_image" in content:
                        insert_columns.append("preview_image")
                        insert_values.append(content["preview_image"])
                    
                    # Thêm seo_title nếu có cột
                    if has_seo_title_column and "seo_title" in content:
                        insert_columns.append("seo_title")
                        insert_values.append(content["seo_title"])
                    
                    # Thêm seo_description nếu có cột
                    if has_seo_description_column and "seo_description" in content:
                        insert_columns.append("seo_description")
                        insert_values.append(content["seo_description"])
                    
                    # Thêm word_count nếu có cột
                    if has_word_count_column and "word_count" in content:
                        insert_columns.append("word_count")
                        insert_values.append(content["word_count"])
                    
                    # Tạo câu lệnh SQL động
                    columns_str = ", ".join(insert_columns)
                    placeholders = ", ".join([f"%s" for _ in insert_values])
                    
                    query = f"""
                    INSERT INTO content ({columns_str})
                    VALUES ({placeholders})
                    RETURNING id, title, created_at
                    """
                    
                    cursor.execute(query, insert_values)
                except Exception as e:
                    print(f"Lỗi khi chèn dữ liệu: {str(e)}")
                    # Nếu có lỗi, sử dụng câu lệnh đơn giản nhất
                    query = """
                    INSERT INTO content (title, content, topic_id)
                    VALUES (%s, %s, %s)
                    RETURNING id, title, created_at
                    """
                    
                    cursor.execute(query, (topic_title, content_json, topic_id))
                result = cursor.fetchone()
                
                conn.commit()
                cursor.close()
                conn.close()
                
                return {
                    "success": True,
                    "content": {
                        "id": result["id"],
                        "title": topic_title,
                        "social_media": content,
                        "topic_id": topic_id,
                        "created_at": result["created_at"],
                        "status": "new",
                        "message": "Đã tạo nội dung mạng xã hội mới và lưu vào cơ sở dữ liệu"
                    }
                }
            else:
                # Trả về nội dung mà không lưu
                return {
                    "success": True,
                    "content": {
                        "id": None,
                        "title": topic_title,
                        "social_media": content,
                        "topic_id": topic_id,
                        "created_at": None,
                        "status": "generated_not_saved",
                        "message": "Đã tạo nội dung mạng xã hội mới nhưng chưa lưu vào cơ sở dữ liệu"
                    }
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }