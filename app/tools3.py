import json
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from database import SupaBaseDB

class NavigationInput(BaseModel):
    product_id: str = Field(description="รหัสสินค้าที่ต้องการหาตำแหน่ง")

class NavigationTool(BaseTool):
    name = "get_location"
    description = "บอกตำแหน่งของสินค้าในห้างสรรพสินค้า"
    args_schema = NavigationInput
    db: SupaBaseDB
    
    def _run(self, product_id: str) -> str:
        product = self.db.get_product_by_id(product_id)
        
        if not product:
            return f"ไม่พบสินค้ารหัส {product_id}"
        
        location = json.loads(product['location_info'])
        zone = location['zone']
        section = location['section']
        shelf = location['shelf']
        level = location['shelf_level']
        
        side = "ขวามือ" if shelf <= 3 else "ซ้ายมือ"
        height = {1: "ชั้นล่าง", 2: "ชั้นกลาง", 3: "ชั้นบน"}[level]
        
        return f"📍 {product['name']} อยู่ที่:\n" \
               f"โซน {zone} แผนก {section}\n" \
               f"ชั้นวางที่ {shelf} ({side}) {height}"
