import json
from typing import List
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from database import SupaBaseDB

class AddToListInput(BaseModel):
    product_id: str = Field(description="รหัสสินค้าที่ต้องการเพิ่มในรายการ")

class ShoppingListTool(BaseTool):
    name = "add_to_shopping_list"
    description = "เพิ่มสินค้าเข้ารายการช้อปปิ้ง"
    args_schema = AddToListInput
    db: SupaBaseDB
    shopping_list: List[str] = []
    
    def _run(self, product_id: str) -> str:
        product = self.db.get_product_by_id(product_id)
        
        if not product:
            return f"ไม่พบสินค้ารหัส {product_id}"
        
        if product_id in self.shopping_list:
            return f"{product['name']} มีในรายการอยู่แล้วค่ะ"
        
        self.shopping_list.append(product_id)
        return f"✅ เพิ่ม {product['name']} เข้ารายการแล้ว (รวม {len(self.shopping_list)} รายการ)"

class RoutePlannerTool(BaseTool):
    name = "summarize_route"
    description = "สรุปเส้นทางการช้อปปิ้งและราคารวม"
    db: SupaBaseDB
    shopping_list: List[str] = []
    
    def _run(self) -> str:
        if not self.shopping_list:
            return "ยังไม่มีสินค้าในรายการค่ะ"
        
        products = [self.db.get_product_by_id(pid) for pid in self.shopping_list]
        products_by_zone = {}
        total_price = 0
        
        for product in products:
            location = json.loads(product['location_info'])
            zone = location['zone']
            if zone not in products_by_zone:
                products_by_zone[zone] = []
            products_by_zone[zone].append(product)
            total_price += product['price']
        
        output = "🗺️ เส้นทางช้อปปิ้งของคุณ:\n\n"
        for zone in sorted(products_by_zone.keys()):
            output += f"โซน {zone}:\n"
            for product in products_by_zone[zone]:
                location = json.loads(product['location_info'])
                output += f"  • {product['name']} - แผนก {location['section']}, ชั้น {location['shelf']}\n"
            output += "\n"
        
        output += f"💰 ราคารวม: {total_price:.2f} บาท"
        return output
