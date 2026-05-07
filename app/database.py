from supabase import create_client, Client
from typing import List, Dict, Optional
from config import Config

class SupaBaseDB:
    def __init__(self, config: Config):
        self.client: Client = create_client(config.supabase_url, config.supabase_key)
        self.table_name = "products"
    
    def search_products(self, embedding: List[float], filters: Optional[Dict] = None, limit: int = 5) -> List[Dict]:
        query = self.client.rpc(
            "match_products",
            {
                "query_embedding": embedding,
                "match_threshold": 0.7,
                "match_count": limit
            }
        )
        
        if filters:
            if "max_price" in filters:
                query = query.lte("price", filters["max_price"])
            if "min_price" in filters:
                query = query.gte("price", filters["min_price"])
            if "category" in filters:
                query = query.eq("category", filters["category"])
        
        return query.execute().data
    
    def check_stock(self, product_id: str) -> Dict:
        result = self.client.table(self.table_name).select("*").eq("id", product_id).execute()
        return result.data[0] if result.data else None
    
    def get_product_by_id(self, product_id: str) -> Dict:
        result = self.client.table(self.table_name).select("*").eq("id", product_id).execute()
        return result.data[0] if result.data else None
