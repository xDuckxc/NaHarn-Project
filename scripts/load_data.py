import pandas as pd
import sys
sys.path.append('/app')

from config import load_config
from database import SupaBaseDB
from embeddings import EmbeddingService

def load_data():
    config = load_config()
    db = SupaBaseDB(config)
    embedder = EmbeddingService(config)
    
    df = pd.read_csv("/data/products.csv")
    
    print(f"Loading {len(df)} products...")
    
    descriptions = df['description'].tolist()
    embeddings = embedder.embed_batch(descriptions)
    
    for idx, row in df.iterrows():
        product_data = {
            "id": row['id'],
            "name": row['name'],
            "brand": row['brand'],
            "category": row['category'],
            "description": row['description'],
            "price": float(row['price']),
            "stock_quantity": int(row['stock_quantity']),
            "location_info": row['location_info'],
            "embedding": embeddings[idx]
        }
        
        db.client.table("products").upsert(product_data).execute()
        
        if (idx + 1) % 50 == 0:
            print(f"Loaded {idx + 1}/{len(df)} products")
    
    print("Data loading complete!")

if __name__ == "__main__":
    load_data()
