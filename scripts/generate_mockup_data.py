import pandas as pd
import random
import json

categories = {
    "อาหาร/เครื่องดื่ม": "A",
    "ของใช้ทั่วไป": "B",
    "เสื้อผ้า": "C",
    "เครื่องใช้ไฟฟ้า": "D",
    "ยาสามัญ": "E"
}

products_data = []
product_id = 1

# อาหาร/เครื่องดื่ม (Zone A)
food_items = [
    ("นมสด", "Meiji", "นมสดรสหวานมัน ดื่มแล้วสดชื่น เหมาะกับเด็กและผู้ใหญ่", 45),
    ("ขนมปัง", "Farmhouse", "ขนมปังนุ่มหอม เหมาะทำแซนด์วิช กินตอนเช้า", 35),
    ("น้ำผลไม้", "Malee", "น้ำส้มคั้นสดชื่น วิตามินซีสูง ดื่มแก้กระหาย", 25),
]

for i in range(100):
    name, brand, desc, base_price = random.choice(food_items)
    products_data.append({
        "id": f"P{product_id:04d}",
        "name": f"{name} {random.choice(['รสธรรมชาติ', 'รสหวาน', 'รสออริจินัล', 'แบบพิเศษ'])}",
        "brand": brand,
        "category": "อาหาร/เครื่องดื่ม",
        "description": desc,
        "price": round(base_price + random.uniform(-10, 20), 2),
        "stock_quantity": random.randint(0, 50),
        "location_info": json.dumps({
            "zone": "A",
            "section": str(random.randint(1, 5)),
            "shelf": str(random.randint(1, 6)),
            "shelf_level": str(random.randint(1, 3))
        })
    })
    product_id += 1

# ของใช้ทั่วไป (Zone B)
household_items = [
    ("ผงซักฟอก", "OMO", "ซักผ้าสะอาด หอมนาน กำจัดคราบดี", 89),
    ("แชมพู", "Sunsilk", "ผมนุ่มลื่น ไม่ฟู ลดผมร่วง", 129),
    ("ยาสีฟัน", "Colgate", "ฟันขาว ลมหายใจสดชื่น ป้องกันฟันผุ", 45),
]

for i in range(100):
    name, brand, desc, base_price = random.choice(household_items)
    products_data.append({
        "id": f"P{product_id:04d}",
        "name": f"{name} {random.choice(['ขนาดใหญ่', 'ขนาดกลาง', 'แบบประหยัด', 'สูตรพิเศษ'])}",
        "brand": brand,
        "category": "ของใช้ทั่วไป",
        "description": desc,
        "price": round(base_price + random.uniform(-20, 30), 2),
        "stock_quantity": random.randint(0, 50),
        "location_info": json.dumps({
            "zone": "B",
            "section": str(random.randint(1, 5)),
            "shelf": str(random.randint(1, 6)),
            "shelf_level": str(random.randint(1, 3))
        })
    })
    product_id += 1

# เสื้อผ้า (Zone C)
clothing_items = [
    ("เสื้อยืด", "Uniqlo", "เสื้อยืดผ้านุ่ม ใส่สบาย ระบายอากาศดี", 299),
    ("กางเกงยีนส์", "Levi's", "กางเกงยีนส์ทรงสวย ใส่ได้ทุกโอกาส", 890),
    ("เสื้อเชิ้ต", "Arrow", "เสื้อเชิ้ตทำงาน ดูดี มีระดับ", 590),
]

for i in range(100):
    name, brand, desc, base_price = random.choice(clothing_items)
    products_data.append({
        "id": f"P{product_id:04d}",
        "name": f"{name} {random.choice(['สีขาว', 'สีดำ', 'สีน้ำเงิน', 'ลายทาง'])}",
        "brand": brand,
        "category": "เสื้อผ้า",
        "description": desc,
        "price": round(base_price + random.uniform(-100, 200), 2),
        "stock_quantity": random.randint(0, 50),
        "location_info": json.dumps({
            "zone": "C",
            "section": str(random.randint(1, 5)),
            "shelf": str(random.randint(1, 6)),
            "shelf_level": str(random.randint(1, 3))
        })
    })
    product_id += 1

# เครื่องใช้ไฟฟ้า (Zone D)
electronics_items = [
    ("หูฟัง", "Sony", "เสียงใส ตัดเสียงรบกวน ใส่สบาย", 1290),
    ("ไฟฉาย", "Eveready", "ไฟสว่าง ใช้งานนาน ฉุกเฉินได้", 159),
    ("พัดลม", "Hatari", "ลมแรง เย็นสบาย ประหยัดไฟ", 890),
]

for i in range(100):
    name, brand, desc, base_price = random.choice(electronics_items)
    products_data.append({
        "id": f"P{product_id:04d}",
        "name": f"{name} {random.choice(['รุ่นใหม่', 'รุ่นประหยัด', 'รุ่นพรีเมียม', 'รุ่นมาตรฐาน'])}",
        "brand": brand,
        "category": "เครื่องใช้ไฟฟ้า",
        "description": desc,
        "price": round(base_price + random.uniform(-200, 500), 2),
        "stock_quantity": random.randint(0, 50),
        "location_info": json.dumps({
            "zone": "D",
            "section": str(random.randint(1, 5)),
            "shelf": str(random.randint(1, 6)),
            "shelf_level": str(random.randint(1, 3))
        })
    })
    product_id += 1

# ยาสามัญ (Zone E)
medicine_items = [
    ("พาราเซตามอล", "Tylenol", "แก้ปวดหัว ลดไข้ ปวดเมื่อยกล้ามเนื้อ", 25),
    ("ยาแก้ท้องเสีย", "Imodium", "ท้องเสีย ท้องร่วง ปวดท้อง รับประทานแล้วหาย", 35),
    ("ยาแก้แพ้", "Zyrtec", "คันจมูก น้ำมูกไหล จาม ผื่นคัน", 45),
]

for i in range(100):
    name, brand, desc, base_price = random.choice(medicine_items)
    products_data.append({
        "id": f"P{product_id:04d}",
        "name": f"{name} {random.choice(['แบบเม็ด', 'แบบน้ำ', 'แบบแคปซูล', 'แบบชนิดพิเศษ'])}",
        "brand": brand,
        "category": "ยาสามัญ",
        "description": desc,
        "price": round(base_price + random.uniform(-10, 30), 2),
        "stock_quantity": random.randint(0, 50),
        "location_info": json.dumps({
            "zone": "E",
            "section": str(random.randint(1, 5)),
            "shelf": str(random.randint(1, 6)),
            "shelf_level": str(random.randint(1, 3))
        })
    })
    product_id += 1

df = pd.DataFrame(products_data)
df.to_csv("data/products.csv", index=False, encoding="utf-8-sig")
print(f"Generated {len(products_data)} products across 5 categories")
