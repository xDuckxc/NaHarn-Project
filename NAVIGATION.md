# Mall Layout & Navigation System

## ภาพรวมโครงสร้างห้าง

### มิติของห้าง
- **ความยาว (X-axis)**: 100 เมตร
- **ความกว้าง (Z-axis)**: 50 เมตร  
- **ความสูง**: 4 เมตร

### โซน (Zones)
ห้างแบ่งเป็น 5 โซน แต่ละโซนกว้าง 20 เมตร:

| โซน | ตำแหน่ง X | หมวดสินค้าหลัก |
|-----|-----------|----------------|
| A | 0-20m | อาหาร |
| B | 20-40m | ของใช้ทั่วไป |
| C | 40-60m | เสื้อผ้า |
| D | 60-80m | เครื่องใช้ไฟฟ้า |
| E | 80-100m | ยาสามัญ |

### Section (แถว)
- แต่ละ section ลึก **3 เมตร** (Z-axis)
- Section เรียงต่อกันตามแนว Z-axis
- Section 1 อยู่ที่ Z = 3m, Section 2 ที่ Z = 6m, ...

### Shelf (ชั้นวาง)
แต่ละ section มี **6 ชั้นวาง** แบ่งเป็น 2 ฝั่ง:

**ฝั่งขวา (Shelf 1-3)**
- Shelf 1: X = zone_start + 1.0m
- Shelf 2: X = zone_start + 3.5m
- Shelf 3: X = zone_start + 6.0m

**ฝั่งซ้าย (Shelf 4-6)**
- Shelf 4: X = zone_end - 8.5m
- Shelf 5: X = zone_end - 6.0m
- Shelf 6: X = zone_end - 3.5m

**ทางเดิน (Aisle)**: กว้าง 2 เมตร อยู่ตรงกลางระหว่าง 2 ฝั่ง

### Shelf Level (ระดับชั้น)
แต่ละชั้นวางมี 3 ระดับ:

| Level | ความสูง (Y) | คำอธิบาย |
|-------|-------------|----------|
| 1 | 0.5m | ชั้นล่างสุด |
| 2 | 1.3m | ระดับสายตา |
| 3 | 2.1m | ชั้นบนสุด |

## ระบบพิกัด 3D

### การคำนวณตำแหน่ง
```python
from scripts.mall_layout_config import get_shelf_position

# ตัวอย่าง: Zone C, Section 5, Shelf 3, Level 2
x, y, z = get_shelf_position("C", 5, 3, 2)
# ผลลัพธ์: (46.0, 1.3, 15.0)
```

### ตัวอย่างพิกัด

| Location | Coordinates | คำอธิบาย |
|----------|-------------|----------|
| Zone A, Sec 1, Shelf 1, Lv 2 | (1.0, 1.3, 3.0) | โซน A ชั้นวางแรกฝั่งขวา ระดับสายตา |
| Zone C, Sec 5, Shelf 3, Lv 1 | (46.0, 0.5, 15.0) | โซน C ชั้นวางที่ 3 ฝั่งขวา ชั้นล่าง |
| Zone E, Sec 3, Shelf 6, Lv 3 | (91.5, 2.1, 9.0) | โซน E ชั้นวางสุดท้ายฝั่งซ้าย ชั้นบน |

## ระบบนำทาง

### Navigation Waypoints
```python
from navigation_utils import get_product_waypoints, calculate_walking_distance

# สร้าง waypoints จากรายการสินค้า
waypoints = get_product_waypoints(products)

# คำนวณระยะทางเดิน
distance = calculate_walking_distance(waypoints)
print(f"ระยะทางรวม: {distance} เมตร")
```

### การเรียงลำดับเส้นทาง
ระบบจะเรียงสินค้าตาม:
1. **Zone** (A → B → C → D → E)
2. **Section** (1 → 2 → 3 → ...)
3. **Shelf** (1 → 2 → ... → 6)

เพื่อให้เดินทางสั้นที่สุดและไม่ต้องย้อนกลับ

## การใช้งาน

### 1. สร้างพิกัด 3D ใหม่
```bash
python3 scripts/generate_3d_coordinates.py
```

### 2. โหลดข้อมูลเข้า Database
```bash
docker compose down -v
docker compose up --build
```

### 3. ทดสอบระบบนำทาง
```bash
python3 test_3d_navigation.py
```

## ไฟล์ที่เกี่ยวข้อง

- `scripts/mall_layout_config.py` — การกำหนดโครงสร้างห้าง
- `scripts/generate_3d_coordinates.py` — สร้างพิกัด 3D
- `navigation_utils.py` — ฟังก์ชันช่วยสำหรับนำทาง
- `mall_products_500_with_3d.csv` — ข้อมูลสินค้าพร้อมพิกัด
