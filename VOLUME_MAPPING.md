# Volume-Based Zone Mapping

## ภาพรวม

ระบบ Volume-Based Mapping ใช้ Bounding Box (กล่องล่องหน) เพื่อกำหนดพื้นที่ของแต่ละ Zone, Section และ Shelf ในห้าง ทำให้สามารถ:
- แสดงขอบเขตโซนแบบ 3D
- ตรวจสอบว่าจุดใดอยู่ในโซนไหน
- สร้าง visual guides ใน 3D viewer

## โครงสร้าง Bounding Box

```python
{
    "min_x": 0.0,      # ขอบซ้าย
    "min_y": 0.0,      # พื้น
    "min_z": 0.0,      # ด้านหน้า
    "max_x": 20.0,     # ขอบขวา
    "max_y": 4.0,      # เพดาน
    "max_z": 50.0,     # ด้านหลัง
    "center_x": 10.0,  # จุดกึ่งกลาง X
    "center_y": 2.0,   # จุดกึ่งกลาง Y
    "center_z": 25.0,  # จุดกึ่งกลาง Z
    "width": 20.0,     # ความกว้าง
    "height": 4.0,     # ความสูง
    "depth": 50.0      # ความลึก
}
```

## Zone Volumes

แต่ละโซนมี bounding box ครอบคลุมพื้นที่ทั้งหมด:

| Zone | X Range | Y Range | Z Range | สี |
|------|---------|---------|---------|-----|
| A | 0-20m | 0-4m | 0-50m | #FF6B6B (แดง) |
| B | 20-40m | 0-4m | 0-50m | #4ECDC4 (เขียวมิ้นท์) |
| C | 40-60m | 0-4m | 0-50m | #45B7D1 (ฟ้า) |
| D | 60-80m | 0-4m | 0-50m | #FFA07A (ส้ม) |
| E | 80-100m | 0-4m | 0-50m | #98D8C8 (เขียวอ่อน) |

## การใช้งาน

### 1. สร้าง Zone Volume

```python
from scripts.zone_volumes import create_zone_volume

# สร้าง bounding box สำหรับ Zone C
bbox = create_zone_volume("C")
print(f"Zone C: {bbox['min_x']} to {bbox['max_x']}m")
```

### 2. ตรวจสอบจุดอยู่ในโซนไหน

```python
from scripts.zone_volumes import get_zone_from_coordinates

# ตรวจสอบว่าจุด (50, 1, 25) อยู่โซนไหน
zone = get_zone_from_coordinates(50.0, 1.0, 25.0)
print(f"Point is in Zone {zone}")  # Output: Zone C
```

### 3. สร้าง Section Volume

```python
from scripts.zone_volumes import create_section_volume

# สร้าง bounding box สำหรับ Zone C, Section 5
bbox = create_section_volume("C", 5)
print(f"Section volume: {bbox['depth']}m deep")
```

### 4. สร้าง Shelf Volume

```python
from scripts.zone_volumes import create_shelf_volume

# สร้าง bounding box สำหรับ Zone A, Section 1, Shelf 3
bbox = create_shelf_volume("A", 1, 3)
print(f"Shelf: {bbox['width']}m × {bbox['depth']}m")
```

## 3D Visualization

### สร้าง Zone Boxes สำหรับ Three.js

```bash
python3 scripts/generate_zone_boxes.py
```

สร้างไฟล์ `zone_boxes.js` ที่มี:
- ข้อมูล bounding box ทุกโซน
- ฟังก์ชัน `createZoneBoxes(scene)` สำหรับแสดงกล่องโซน
- สีและความโปร่งใสของแต่ละโซน

### ใน Three.js

```javascript
// โหลด zone_boxes.js แล้วเรียกใช้
const boxes = createZoneBoxes(scene);

// Zone boxes จะแสดงเป็นกล่องโปร่งใสพร้อม wireframe
// - opacity: 0.1 (โปร่งใสมาก)
// - wireframe edges สีตามโซน
```

## ไฟล์ที่เกี่ยวข้อง

- `scripts/zone_volumes.py` — คำนวณ bounding boxes
- `scripts/generate_zone_boxes.py` — สร้าง JavaScript สำหรับ Three.js
- `static/zone_boxes.js` — ข้อมูลโซนสำหรับ 3D viewer
- `public/zone_boxes.js` — Copy สำหรับ Chainlit

## ตัวอย่างผลลัพธ์

```
Zone A:
  X: 0.0 to 20.0m
  Y: 0.0 to 4.0m
  Z: 0.0 to 50.0m
  Center: (10.0, 2.0, 25.0)
  Dimensions: 20.0 × 4.0 × 50.0m

Section Volume (Zone C, Section 5):
  X: 40.0 to 60.0m
  Z: 12.0 to 15.0m

Shelf Volume (Zone A, Section 1, Shelf 3):
  X: 6.0 to 8.5m
  Z: 0.0 to 0.8m
```

## การทดสอบ

```bash
# ทดสอบ zone volumes
python3 scripts/zone_volumes.py

# สร้าง zone boxes สำหรับ 3D
python3 scripts/generate_zone_boxes.py

# ดูผลลัพธ์ใน 3D viewer
# http://localhost:8000/public/model_viewer.html
```
