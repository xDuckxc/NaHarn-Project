# Detailed Bounding Boxes (Sections & Shelves)

## ภาพรวม

ระบบ Detailed Bounding Boxes แสดงกล่องย่อยภายในแต่ละ Zone:
- **Section Boxes** — แสดงแต่ละแถว (สีเทา)
- **Shelf Boxes** — แสดงแต่ละชั้นวาง (สีเขียว/ฟ้า)

## โครงสร้าง

### Zone Boxes (ระดับบนสุด)
```
Zone A (20m × 4m × 50m)
├── Section 1 (20m × 4m × 3m)
│   ├── Shelf 1 (2.5m × 4m × 0.8m) [ฝั่งขวา]
│   ├── Shelf 2 (2.5m × 4m × 0.8m) [ฝั่งขวา]
│   ├── Shelf 3 (2.5m × 4m × 0.8m) [ฝั่งขวา]
│   ├── Shelf 4 (2.5m × 4m × 0.8m) [ฝั่งซ้าย]
│   ├── Shelf 5 (2.5m × 4m × 0.8m) [ฝั่งซ้าย]
│   └── Shelf 6 (2.5m × 4m × 0.8m) [ฝั่งซ้าย]
├── Section 2 (20m × 4m × 3m)
└── ...
```

## การใช้งาน

### 1. สร้าง Detailed Boxes

```bash
python3 scripts/generate_detailed_boxes.py
```

สร้างไฟล์:
- `static/detailed_boxes.js`
- `public/detailed_boxes.js`

### 2. ใน 3D Viewer

เปิด http://localhost:8000/public/model_viewer.html

**Toggle Controls:**
- ☑️ **แสดง Sections** — แสดงกล่องแถว (สีเทา)
- ☑️ **แสดง Shelves** — แสดงกล่องชั้นวาง (สีเขียว/ฟ้า)

### 3. ใน JavaScript

```javascript
// แสดงเฉพาะ sections
createDetailedBoxes(scene, true, false);

// แสดงเฉพาะ shelves
createDetailedBoxes(scene, false, true);

// แสดงทั้งหมด
createDetailedBoxes(scene, true, true);
```

## ข้อมูล Bounding Boxes

### Section Box
```javascript
{
    zone: 'A',
    section: 1,
    x: 10.0,      // จุดกึ่งกลาง X
    y: 2.0,       // จุดกึ่งกลาง Y
    z: 1.5,       // จุดกึ่งกลาง Z
    w: 20.0,      // ความกว้าง (ครอบคลุมทั้งโซน)
    h: 4.0,       // ความสูง
    d: 3.0,       // ความลึก (1 section)
    color: 0x888888  // สีเทา
}
```

### Shelf Box
```javascript
{
    zone: 'A',
    section: 1,
    shelf: 1,
    x: 2.25,      // ตำแหน่งชั้นวาง
    y: 2.0,
    z: 1.5,
    w: 2.5,       // ความกว้างชั้นวาง
    h: 4.0,
    d: 0.8,       // ความลึกชั้นวาง
    color: 0x00FF00  // สีเขียว (ฝั่งขวา)
}
```

## สีของ Boxes

| Type | Color | Hex | คำอธิบาย |
|------|-------|-----|----------|
| Zone | ตามโซน | 0xFF6B6B, ... | แต่ละโซนสีต่างกัน |
| Section | เทา | 0x888888 | ทุก section สีเดียวกัน |
| Shelf (1-3) | เขียว | 0x00FF00 | ฝั่งขวา |
| Shelf (4-6) | ฟ้า | 0x0000FF | ฝั่งซ้าย |

## จำนวน Boxes ที่สร้าง

### Default Configuration
- **Sections**: 25 boxes (5 zones × 5 sections)
- **Shelves**: 6 boxes (Zone A, Section 1 เท่านั้น)

### เพิ่ม Shelves สำหรับโซนอื่น

แก้ไข `scripts/generate_detailed_boxes.py`:

```python
def generate_all_detailed_boxes():
    all_boxes = {
        "sections": [],
        "shelves": []
    }
    
    # Generate sections for all zones
    for zone in ["A", "B", "C", "D", "E"]:
        all_boxes["sections"].extend(generate_section_boxes(zone, max_sections=5))
    
    # Generate shelves for multiple sections
    all_boxes["shelves"].extend(generate_shelf_boxes("A", 1))
    all_boxes["shelves"].extend(generate_shelf_boxes("A", 2))  # เพิ่ม Section 2
    all_boxes["shelves"].extend(generate_shelf_boxes("B", 1))  # เพิ่ม Zone B
    
    return all_boxes
```

## การปรับแต่ง

### เปลี่ยนสี Section

```python
boxes.append({
    # ...
    "color": 0xFF0000  # เปลี่ยนเป็นสีแดง
})
```

### เปลี่ยนขนาด Shelf

```python
boxes.append({
    # ...
    "w": 3.0,  # กว้างขึ้น
    "d": 1.0,  # ลึกขึ้น
})
```

### แสดงเฉพาะ Zone C

```python
def generate_all_detailed_boxes():
    all_boxes = {
        "sections": [],
        "shelves": []
    }
    
    # เฉพาะ Zone C
    all_boxes["sections"].extend(generate_section_boxes("C", max_sections=5))
    all_boxes["shelves"].extend(generate_shelf_boxes("C", 1))
    
    return all_boxes
```

## ตัวอย่างผลลัพธ์

```
✓ Generated static/detailed_boxes.js
✓ Sections: 25
✓ Shelves: 6

Sample Section Box (Zone A, Section 1):
  {'zone': 'A', 'section': 1, 'x': 10.0, 'y': 2.0, 'z': 1.5, 
   'w': 20.0, 'h': 4.0, 'd': 3.0, 'color': 8947848}

Sample Shelf Box (Zone A, Section 1, Shelf 1):
  {'zone': 'A', 'section': 1, 'shelf': 1, 'x': 2.25, 'y': 2.0, 'z': 1.5,
   'w': 2.5, 'h': 4.0, 'd': 0.8, 'color': 65280}
```

## การทดสอบ

1. สร้าง detailed boxes:
   ```bash
   python3 scripts/generate_detailed_boxes.py
   ```

2. Copy และ restart:
   ```bash
   cp templates/model_viewer.html public/model_viewer.html
   docker compose restart app-ui
   ```

3. เปิด 3D viewer และทดสอบ toggle:
   ```
   http://localhost:8000/public/model_viewer.html
   ```

## Tips

- **Performance**: ถ้าแสดง shelves ทุกโซนจะมีกล่องเยอะมาก (5 zones × 5 sections × 6 shelves = 150 boxes)
- **Dev Mode**: แสดงเฉพาะที่ต้องการเพื่อความชัดเจน
- **Color Coding**: ใช้สีแยกประเภทเพื่อง่ายต่อการมองเห็น
