from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_community.vectorstores import SupabaseVectorStore
from langchain_openai import OpenAIEmbeddings
from config.settings import OPENAI_API_KEY, MODEL_NAME, EMBEDDING_MODEL
from app.utils.database import get_supabase_client, fetch_data
from app.services.embedding_service import EmbeddingService
import json
import requests
import base64
from openai import OpenAI

class RAGService:
    def __init__(self):
        self.openai = ChatOpenAI(
            model_name=MODEL_NAME,
            openai_api_key=OPENAI_API_KEY,
            temperature=0.7
        )
        self.embedding_service = EmbeddingService()
        self.supabase = get_supabase_client()
        
    def setup_vector_store(self, table_name, embedding_column="embedding"):
        """
        Setup a vector store using Supabase.
        
        Args:
            table_name (str): The table name to use
            embedding_column (str): The column name containing embeddings
            
        Returns:
            SupabaseVectorStore: A vector store instance
        """
        embeddings = OpenAIEmbeddings(
            model=EMBEDDING_MODEL,
            openai_api_key=OPENAI_API_KEY
        )
        
        vector_store = SupabaseVectorStore(
            client=self.supabase,
            embedding=embeddings,
            table_name=table_name,
            query_name="match_documents"
        )
        
        return vector_store
    
    def create_topic_generator(self, product_context, brand_info=None, previous_topics=None):
        """
        Create a topic generator based on product information, brand info and previous topics.
        
        Args:
            product_context (str): Product information to base topics on
            brand_info (str, optional): Brand information for context
            previous_topics (list, optional): List of previous topics
            
        Returns:
            function: A function that generates topics
        """
        topic_template = """
        Bạn là một chuyên gia sáng tạo nội dung và tiếp thị.
        
        Dựa trên thông tin sau đây, hãy tạo ra một chủ đề hấp dẫn và thân thiện với SEO:
        
        Thông tin sản phẩm:
        {product_info}
        
        {brand_context}
        
        {previous_topics_context}
        
        Tạo ra một chủ đề mà:
        1. Liên quan đến sản phẩm và phù hợp với định vị thương hiệu
        2. Có khả năng thu hút khách hàng tiềm năng
        3. Mang lại giá trị cho người đọc
        4. Được tối ưu hóa cho công cụ tìm kiếm
        5. Phù hợp cho tiếp thị nội dung
        6. KHÔNG trùng lặp với các chủ đề đã có (nếu có)
        7. Có tính độc đáo và sáng tạo
        
        Chỉ tạo tiêu đề chủ đề mà không có thêm giải thích hoặc bình luận nào khác.
        """
        
        # Prepare context
        brand_context = "Thông tin thương hiệu:\n" + brand_info if brand_info else ""
        
        previous_topics_context = ""
        if previous_topics and len(previous_topics) > 0:
            previous_topics_context = "Các chủ đề đã có:\n" + "\n".join([f"- {topic}" for topic in previous_topics])
        
        topic_prompt = PromptTemplate(
            template=topic_template,
            input_variables=["product_info", "brand_context", "previous_topics_context"]
        )
        
        def generate_topic():
            formatted_prompt = topic_prompt.format(
                product_info=product_context,
                brand_context=brand_context,
                previous_topics_context=previous_topics_context
            )
            response = self.openai.invoke(formatted_prompt)
            return response.content
        
        return generate_topic
    
    def create_multiple_topics_generator(self, product_context, brand_info, count=3):
        """
        Create a generator for multiple topics based on product and brand information.
        
        Args:
            product_context (str): Product information to base topics on
            brand_info (str): Brand information to provide context
            count (int): Number of topics to generate
            
        Returns:
            function: A function that generates multiple topics in JSON format
        """
        topic_template = """
        Bạn là một chuyên gia sáng tạo nội dung và tiếp thị.
        
        Dựa trên thông tin sản phẩm và thương hiệu sau đây, hãy tạo ra {count} ý tưởng chủ đề hấp dẫn và thân thiện với SEO:
        
        Thông tin sản phẩm:
        {product_info}
        
        Thông tin thương hiệu:
        {brand_info}
        
        Tạo ra các chủ đề mà:
        1. Liên quan đến sản phẩm và phù hợp với định vị thương hiệu
        2. Có khả năng thu hút khách hàng tiềm năng
        3. Mang lại giá trị cho người đọc
        4. Được tối ưu hóa cho công cụ tìm kiếm
        5. Phù hợp cho tiếp thị nội dung
        
        Trả lời dưới dạng JSON CHÍNH XÁC theo định dạng sau:
        {{
            "topics": [
                {{
                    "title": "Tiêu đề chủ đề 1",
                    "relevance_score": 85,
                    "seo_keywords": ["từ khóa 1", "từ khóa 2", "từ khóa 3"],
                    "target_audience": "Mô tả đối tượng mục tiêu"
                }},
                {{
                    "title": "Tiêu đề chủ đề 2",
                    "relevance_score": 80,
                    "seo_keywords": ["từ khóa 1", "từ khóa 2", "từ khóa 3"],
                    "target_audience": "Mô tả đối tượng mục tiêu"
                }},
                ...
            ]
        }}
        
        Chỉ trả về JSON, không thêm giải thích hay bình luận nào khác.
        """
        
        topic_prompt = PromptTemplate(
            template=topic_template,
            input_variables=["product_info", "brand_info", "count"]
        )
        
        def generate_topics():
            formatted_prompt = topic_prompt.format(
                product_info=product_context,
                brand_info=brand_info,
                count=count
            )
            response = self.openai.invoke(formatted_prompt)
            
            # Ensure the response is valid JSON
            try:
                result = json.loads(response.content)
                return result
            except json.JSONDecodeError:
                # Fallback: If response isn't valid JSON, try to extract JSON
                content = response.content
                start_idx = content.find('{')
                end_idx = content.rfind('}') + 1
                
                if start_idx >= 0 and end_idx > start_idx:
                    json_content = content[start_idx:end_idx]
                    try:
                        result = json.loads(json_content)
                        return result
                    except:
                        pass
                
                # If all parsing attempts fail, return a formatted error
                return {
                    "error": "Không thể định dạng phản hồi thành JSON",
                    "raw_content": content,
                    "topics": []
                }
        
        return generate_topics
    
    def create_content_generator(self, topic, related_content=None):
        """
        Create a content generator based on a topic and optional related content.
        
        Args:
            topic (str): The topic to generate content for
            related_content (list, optional): List of related content as context
            
        Returns:
            function: A function that generates content
        """
        content_template = """
        Bạn là một chuyên gia sáng tạo nội dung chuyên về việc tạo ra nội dung hấp dẫn, thông tin và thân thiện với SEO bằng tiếng Việt.
        
        Nhiệm vụ: Viết nội dung chất lượng cao về chủ đề sau:
        Chủ đề: {topic}
        
        Thông tin/ngữ cảnh bổ sung:
        {context}
        
        Hướng dẫn:
        1. Viết với giọng điệu rõ ràng, hấp dẫn và mang tính trò chuyện
        2. Bao gồm thông tin liên quan từ ngữ cảnh được cung cấp
        3. Tổ chức nội dung với các tiêu đề và tiêu đề phụ phù hợp
        4. Đưa ra lời khuyên thực tế hoặc hiểu biết có thể thực hiện được khi có liên quan
        5. Giữ cho nội dung tập trung vào chủ đề
        6. Hướng tới một bài viết toàn diện nhưng ngắn gọn (khoảng 800-1200 từ)
        7. Sử dụng từ ngữ và cách diễn đạt bằng tiếng Việt tự nhiên, dễ hiểu
        
        Định dạng nội dung bằng Markdown.
        """
        
        content_prompt = PromptTemplate(
            template=content_template,
            input_variables=["topic", "context"]
        )
        
        def generate_content():
            context = ""
            if related_content:
                context = "\n\n".join([f"- {item}" for item in related_content])
            else:
                context = "Không có ngữ cảnh bổ sung nào được cung cấp. Hãy tạo nội dung gốc dựa trên chủ đề."
                
            formatted_prompt = content_prompt.format(topic=topic, context=context)
            response = self.openai.invoke(formatted_prompt)
            return response.content
        
        return generate_content
    
    def retrieve_relevant_products(self, query, limit=5):
        """
        Retrieve relevant products for a given query.
        
        Args:
            query (str): The search query
            limit (int): Maximum number of products to retrieve
            
        Returns:
            list: List of relevant products
        """
        vector_store = self.setup_vector_store("products")
        results = vector_store.similarity_search(query, k=limit)
        return [doc.page_content for doc in results]
    
    def retrieve_related_content(self, topic, limit=3):
        """
        Retrieve related content for a given topic.
        
        Args:
            topic (str): The topic to find related content for
            limit (int): Maximum number of content pieces to retrieve
            
        Returns:
            list: List of related content
        """
        vector_store = self.setup_vector_store("content")
        results = vector_store.similarity_search(topic, k=limit)
        return [doc.page_content for doc in results]
    
    def retrieve_brand_info(self, brand_id):
        """
        Retrieve information about a brand.
        
        Args:
            brand_id (str): ID of the brand to retrieve
            
        Returns:
            str: Formatted brand information
        """
        brand_data = fetch_data("brands", f"id = '{brand_id}'")
        if not brand_data:
            return None
        
        brand = brand_data[0]
        
        # Get brand knowledge if available
        brand_knowledge = fetch_data("brand_knowledge", f"brand_id = '{brand_id}'")
        
        brand_info = f"Tên thương hiệu: {brand.get('name', '')}\n"
        brand_info += f"Mô tả: {brand.get('description', '')}\n"
        
        if brand_knowledge:
            for knowledge in brand_knowledge:
                brand_info += f"\nKiến thức thương hiệu: {knowledge.get('content', '')}\n"
        
        return brand_info
    
    def generate_topic_from_product(self, product_id=None, product_query=None):
        """
        Generate a topic based on a product.
        
        Args:
            product_id (str, optional): ID of the product to base the topic on
            product_query (str, optional): Query to find relevant products
            
        Returns:
            str: Generated topic
        """
        product_context = ""
        
        if product_id:
            # Fetch specific product from database
            from app.utils.database import fetch_data
            products = fetch_data("products", f"id = '{product_id}'")
            if products:
                product = products[0]
                product_context = f"Tên sản phẩm: {product.get('name', '')}\nMô tả: {product.get('description', '')}"
        elif product_query:
            # Retrieve relevant products based on query
            products = self.retrieve_relevant_products(product_query)
            product_context = "\n\n".join(products)
        
        if not product_context:
            raise ValueError("Không tìm thấy thông tin sản phẩm.")
        
        # Create and execute topic generator
        topic_generator = self.create_topic_generator(product_context)
        return topic_generator()
    
    def generate_topics_for_brand_product(self, product_id, brand_id, count=3):
        """
        Generate multiple topics for a product from a specific brand.
        
        Args:
            product_id (str): ID of the product to base topics on
            brand_id (str): ID of the brand
            count (int): Number of topics to generate
            
        Returns:
            dict: JSON object with generated topics
        """
        # Fetch product information
        product_data = fetch_data("products", f"id = '{product_id}'")
        if not product_data:
            return {
                "error": "Không tìm thấy sản phẩm",
                "topics": []
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
        brand_info = self.retrieve_brand_info(brand_id)
        if not brand_info:
            brand_info = "Không có thông tin về thương hiệu."
        
        # Create and execute multiple topics generator
        topics_generator = self.create_multiple_topics_generator(product_context, brand_info, count)
        return topics_generator()
    
    def generate_content_from_topic(self, topic, with_related=True):
        """
        Generate content based on a topic.
        
        Args:
            topic (str): The topic to generate content for
            with_related (bool): Whether to include related content as context
            
        Returns:
            str: Generated content
        """
        related_content = None
        
        if with_related:
            related_content = self.retrieve_related_content(topic)
        
        # Create and execute content generator
        content_generator = self.create_content_generator(topic, related_content)
        return content_generator()

    def generate_topic_from_context(self, product_context, brand_info=None, previous_topics=None, prompt=None):
        """
        Generate a topic based on all available context.
        
        Args:
            product_context (str): Product information
            brand_info (str, optional): Brand information
            previous_topics (list, optional): List of previous topics
            prompt (str, optional): Additional prompt instructions
            
        Returns:
            str: Generated topic
        """
        # Create topic generator with all context
        topic_generator = self.create_topic_generator(
            product_context=product_context,
            brand_info=brand_info,
            previous_topics=previous_topics
        )
        
        # Generate topic
        topic = topic_generator()
        
        # If prompt is provided, validate/refine the topic
        if prompt:
            topic = self.refine_topic_with_prompt(topic, prompt)
        
        return topic 

    def refine_topic_with_prompt(self, topic, prompt):
        """
        Validate and refine a topic based on additional prompt instructions.
        
        Args:
            topic (str): The generated topic to refine
            prompt (str): Additional instructions for refinement
            
        Returns:
            str: Refined topic
        """
        refine_template = """
        Bạn là một chuyên gia sáng tạo nội dung và tiếp thị.
        
        Chủ đề hiện tại:
        {topic}
        
        Yêu cầu bổ sung:
        {prompt}
        
        Nhiệm vụ của bạn:
        1. Đánh giá chủ đề hiện tại dựa trên yêu cầu bổ sung
        2. Điều chỉnh chủ đề để đáp ứng tốt hơn các yêu cầu này
        3. Đảm bảo giữ nguyên ý chính và tính liên quan của chủ đề
        4. Trả về chủ đề đã được điều chỉnh
        
        Chỉ trả về chủ đề đã điều chỉnh, không thêm giải thích hoặc bình luận nào khác.
        """
        
        refine_prompt = PromptTemplate(
            template=refine_template,
            input_variables=["topic", "prompt"]
        )
        
        formatted_prompt = refine_prompt.format(topic=topic, prompt=prompt)
        response = self.openai.invoke(formatted_prompt)
        return response.content 
        
    def generate_image_from_content(self, content, size="1024x1024"):
        """
        Tạo ảnh từ nội dung sử dụng OpenAI DALL-E.
        
        Args:
            content (str): Nội dung để tạo ảnh
            size (str): Kích thước ảnh (mặc định: 1024x1024)
            
        Returns:
            dict: Thông tin ảnh đã tạo bao gồm URL và base64 data
        """
        try:
            # Tạo mô tả ảnh từ nội dung
            image_prompt_template = """
            Bạn là một chuyên gia tạo mô tả hình ảnh cho AI tạo ảnh.
            
            Dựa trên nội dung sau đây, hãy tạo ra một mô tả hình ảnh chi tiết, rõ ràng và hấp dẫn bằng tiếng Anh:
            
            {content}
            
            Mô tả hình ảnh nên:
            1. Chi tiết và cụ thể
            2. Dễ hình dung
            3. Phù hợp với nội dung
            4. Tối đa 100 từ
            5. Bằng tiếng Anh
            
            Chỉ trả về mô tả hình ảnh, không thêm giải thích hoặc bình luận nào khác.
            """
            
            image_prompt = PromptTemplate(
                template=image_prompt_template,
                input_variables=["content"]
            )
            
            formatted_prompt = image_prompt.format(content=content)
            image_description = self.openai.invoke(formatted_prompt).content
            
            # Sử dụng OpenAI API để tạo ảnh
            client = OpenAI(api_key=OPENAI_API_KEY)
            response = client.images.generate(
                model="dall-e-3",
                prompt=image_description,
                size=size,
                quality="standard",
                n=1,
                response_format="b64_json"
            )
            
            # Lấy thông tin ảnh
            image_data = response.data[0].b64_json
            
            # Trả về thông tin ảnh
            return {
                "description": image_description,
                "base64_data": image_data,
                "format": "png"
            }
            
        except Exception as e:
            print(f"Lỗi khi tạo ảnh: {str(e)}")
            return None