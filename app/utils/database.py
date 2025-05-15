import psycopg2
from psycopg2.extras import RealDictCursor
from supabase import create_client
from config.settings import SUPABASE_URL, SUPABASE_KEY, DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT

def get_supabase_client():
    """
    Create and return a Supabase client.
    """
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def get_db_connection():
    """
    Create and return a connection to the PostgreSQL database using connection pooler.
    """
    try:
        # Connection parameters
        params = {
            'host': DB_HOST,
            'port': DB_PORT,  # Connection pooler port from settings
            'database': DB_NAME if DB_NAME else 'postgres',
            'user': DB_USER,
            'password': DB_PASSWORD,
            'sslmode': 'require',
            'options': '-c statement_timeout=60000',  # 60 seconds timeout
            'cursor_factory': RealDictCursor
        }
        
        conn = psycopg2.connect(**params)
        return conn
    except Exception as e:
        print(f"Error connecting to the database: {e}")
        raise

def fetch_data(table_name, condition=None, limit=None):
    """
    Fetch data from a specified table with optional conditions and limit.
    
    Args:
        table_name (str): The name of the table to query
        condition (str, optional): SQL WHERE condition
        limit (int, optional): Limit the number of records to return
        
    Returns:
        list: List of records as dictionaries
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = f"SELECT * FROM {table_name}"
    if condition:
        query += f" WHERE {condition}"
    if limit:
        query += f" LIMIT {limit}"
    
    cursor.execute(query)
    data = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return data 