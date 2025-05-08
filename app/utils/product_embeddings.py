from app.services.embedding_service import EmbeddingService
from app.utils.database import get_db_connection, fetch_data
import json

class ProductEmbeddings:
    def __init__(self):
        self.embedding_service = EmbeddingService()
    
    def generate_product_embedding(self, product_id):
        """
        Generate and store embedding for a product.
        
        Args:
            product_id (str): ID of the product to generate embedding for
            
        Returns:
            dict: Result of the operation
        """
        try:
            # Fetch product data
            products = fetch_data("products", f"id = '{product_id}'")
            if not products:
                return {
                    "success": False,
                    "error": f"Product with ID {product_id} not found"
                }
            
            product = products[0]
            
            # Create text representation of product
            product_text = f"Product: {product.get('name', '')}\n"
            product_text += f"Description: {product.get('description', '')}\n"
            
            if product.get('features'):
                features = product.get('features')
                if isinstance(features, str):
                    try:
                        features = json.loads(features)
                    except:
                        pass
                
                if isinstance(features, list):
                    product_text += "Features:\n"
                    for feature in features:
                        product_text += f"- {feature}\n"
            
            # Generate embedding
            embedding = self.embedding_service.generate_embedding(product_text)
            
            # Store embedding in database
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Update product with embedding
            query = """
            UPDATE products
            SET embedding = %s
            WHERE id = %s
            RETURNING id
            """
            
            cursor.execute(query, (embedding, product_id))
            result = cursor.fetchone()
            
            conn.commit()
            cursor.close()
            conn.close()
            
            if result:
                return {
                    "success": True,
                    "product_id": result["id"]
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to update product embedding"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def generate_all_product_embeddings(self):
        """
        Generate and store embeddings for all products without embeddings.
        
        Returns:
            dict: Result of the operation
        """
        try:
            # Fetch products without embeddings
            products = fetch_data("products", "embedding IS NULL")
            
            if not products:
                return {
                    "success": True,
                    "message": "No products found without embeddings",
                    "count": 0
                }
            
            success_count = 0
            failed_products = []
            
            # Generate embeddings for each product
            for product in products:
                result = self.generate_product_embedding(product["id"])
                
                if result["success"]:
                    success_count += 1
                else:
                    failed_products.append({
                        "id": product["id"],
                        "error": result["error"]
                    })
            
            return {
                "success": True,
                "total": len(products),
                "successful": success_count,
                "failed": len(failed_products),
                "failed_products": failed_products
            }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            } 