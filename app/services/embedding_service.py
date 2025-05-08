import numpy as np
from langchain_openai import OpenAIEmbeddings
from config.settings import OPENAI_API_KEY, EMBEDDING_MODEL
from app.utils.database import get_db_connection

class EmbeddingService:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(
            model=EMBEDDING_MODEL,
            openai_api_key=OPENAI_API_KEY
        )
    
    def generate_embedding(self, text):
        """
        Generate an embedding vector for the given text.
        
        Args:
            text (str): Text to generate embeddings for
            
        Returns:
            list: Embedding vector
        """
        try:
            embedding = self.embeddings.embed_query(text)
            return embedding
        except Exception as e:
            print(f"Error generating embedding: {e}")
            raise
    
    def fetch_embeddings_from_db(self, table_name, column_name, condition=None):
        """
        Fetch embeddings from the database.
        
        Args:
            table_name (str): Name of the table containing embeddings
            column_name (str): Name of the column containing embeddings
            condition (str, optional): SQL WHERE condition
            
        Returns:
            list: List of embedding records
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = f"SELECT id, {column_name} FROM {table_name}"
        if condition:
            query += f" WHERE {condition}"
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return results
    
    def store_embedding(self, table_name, data):
        """
        Store embedding in the database.
        
        Args:
            table_name (str): Table to store embedding in
            data (dict): Data to store including embedding vector
            
        Returns:
            dict: Created record
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["%s"] * len(data))
        
        query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders}) RETURNING *"
        
        cursor.execute(query, list(data.values()))
        result = cursor.fetchone()
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return result
    
    def calculate_similarity(self, query_embedding, document_embedding):
        """
        Calculate cosine similarity between query and document embeddings.
        
        Args:
            query_embedding (list): Query embedding vector
            document_embedding (list): Document embedding vector
            
        Returns:
            float: Similarity score
        """
        query_array = np.array(query_embedding)
        doc_array = np.array(document_embedding)
        
        # Calculate cosine similarity
        dot_product = np.dot(query_array, doc_array)
        query_norm = np.linalg.norm(query_array)
        doc_norm = np.linalg.norm(doc_array)
        
        similarity = dot_product / (query_norm * doc_norm)
        return similarity
    
    def search_by_similarity(self, query, stored_embeddings, threshold=0.7):
        """
        Search for similar documents by comparing embeddings.
        
        Args:
            query (str): Query text
            stored_embeddings (list): List of stored embeddings with metadata
            threshold (float): Minimum similarity score
            
        Returns:
            list: List of similar documents with scores
        """
        query_embedding = self.generate_embedding(query)
        results = []
        
        for item in stored_embeddings:
            document_embedding = item.get('embedding')
            if document_embedding:
                similarity = self.calculate_similarity(query_embedding, document_embedding)
                if similarity >= threshold:
                    results.append({
                        "id": item.get("id"),
                        "score": similarity,
                        "data": item
                    })
        
        # Sort by similarity score (descending)
        results.sort(key=lambda x: x["score"], reverse=True)
        return results 