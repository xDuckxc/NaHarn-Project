from typing import Dict
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from database import SupaBaseDB
from embeddings import EmbeddingService

class StockInput(BaseModel):
    product_id: str = Field(description="รหัสสินค้าที่ต้องการตรวจสอบ")

class StockCheckerTool(BaseTool):
    name = "check_stock"
    description = "ตรวจสอบสต็อกสินค้า หากหมดจะแนะนำสินค้าทดแทน"
    args_schema = StockInput
    db: SupaBaseDB
    embedder: EmbeddingService
    
    def _run(self, product_id: str) -> str:
        product = self.db.check_stock(product_id)
        
        if not product:
            return f"ไม่พบสินค้ารหัส {product_id}"
        
        if product['stock_quantity'] > 0:
            return f"✅ {product['name']} มีสินค้าคงเหลือ {product['stock_quantity']} ชิ้น"
        else:
            embedding = self.embedder.embed_text(product['description'])
            alternatives = self.db.search_products(embedding, limit=3)
            
            output = f"❌ {product['name']} หมดสต็อกแล้วค่ะ\n\n"
            output += "แนะนำสินค้าทดแทน:\n"
            for alt in alternatives:
                if alt['id'] != product_id and alt['stock_quantity'] > 0:
                    output += f"- {alt['name']} ({alt['brand']}) ราคา {alt['price']:.2f} บาท\n"
            
            return output
