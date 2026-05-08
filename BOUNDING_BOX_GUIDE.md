# วิธีปรับแก้ Bounding Box

## ตำแหน่งใน Code

ไฟล์: `templates/model_viewer.html` (บรรทัดประมาณ 88-95)

```javascript
const zoneBoxes = [
    { zone: 'A', color: 0xFF6B6B, x: 10, y: 2, z: 25, w: 20, h: 4, d: 50 },
    { zone: 'B', color: 0x4ECDC4, x: 30, y: 2, z: 25, w: 20, h: 4, d: 50 },
    { zone: 'C', color: 0x45B7D1, x: 50, y: 2, z: 25, w: 20, h: 4, d: 50 },
    { zone: 'D', color: 0xFFA07A, x: 70, y: 2, z: 25, w: 20, h: 4, d: 50 },
    { zone: 'E', color: 0x98D8C8, x: 90, y: 2, z: 25, w: 20, h: 4, d: 50 }
];
```

## พารามิเตอร์

| Parameter | คำอธิบาย | หน่วย |
|-----------|----------|-------|
| `x` | ตำแหน่งกึ่งกลาง X-axis | เมตร |
| `y` | ตำแหน่งกึ่งกลาง Y-axis (ความสูง) | เมตร |
| `z` | ตำแหน่งกึ่งกลาง Z-axis | เมตร |
| `w` | ความกว้าง (width) | เมตร |
| `h` | ความสูง (height) | เมตร |
| `d` | ความลึก (depth) | เมตร |
| `color` | สีเส้นกรอบ (hex) | - |

## ตัวอย่างการปรับแก้

### 1. เปลี่ยนขนาดกล่อง Zone A

```javascript
// เดิม
{ zone: 'A', color: 0xFF6B6B, x: 10, y: 2, z: 25, w: 20, h: 4, d: 50 }

// ใหม่ - กว้างขึ้น 25m, สูงขึ้น 5m
{ zone: 'A', color: 0xFF6B6B, x: 10, y: 2.5, z: 25, w: 25, h: 5, d: 50 }
```

### 2. เลื่อนตำแหน่ง Zone B

```javascript
// เดิม
{ zone: 'B', color: 0x4ECDC4, x: 30, y: 2, z: 25, w: 20, h: 4, d: 50 }

// ใหม่ - เลื่อนไปทาง X +5m, Z -10m
{ zone: 'B', color: 0x4ECDC4, x: 35, y: 2, z: 15, w: 20, h: 4, d: 50 }
```

### 3. เปลี่ยนสีเส้นกรอบ

```javascript
// สีแดง
color: 0xFF0000

// สีเขียว
color: 0x00FF00

// สีฟ้า
color: 0x0000FF

// สีเหลือง
color: 0xFFFF00
```

### 4. ทำให้กล่องแคบลง (เหมาะกับทางเดิน)

```javascript
// กล่องแคบสำหรับทางเดิน
{ zone: 'Aisle', color: 0xFFFFFF, x: 50, y: 0.5, z: 25, w: 2, h: 1, d: 50 }
```

## ขั้นตอนการแก้ไข

1. **แก้ไขไฟล์**
   ```bash
   nano templates/model_viewer.html
   # หรือใช้ editor ที่ชอบ
   ```

2. **หาบรรทัด zoneBoxes** (ประมาณบรรทัด 88)

3. **แก้ค่าตามต้องการ**

4. **Copy และ Restart**
   ```bash
   cp templates/model_viewer.html public/model_viewer.html
   docker compose restart app-ui
   ```

5. **รีเฟรชเว็บ**
   ```
   http://localhost:8000/public/model_viewer.html
   ```

## เคล็ดลับ

### หาตำแหน่งที่เหมาะสม
- ใช้ Grid Helper (เส้นตาราง) เป็นแนวอ้างอิง
- 1 ช่อง grid = 5 เมตร
- กล่องควรอยู่เหนือพื้น (y > 0)

### ขนาดที่แนะนำ
- **Zone**: w=20, h=4, d=50 (ครอบคลุมทั้งโซน)
- **Section**: w=20, h=4, d=3 (แถวเดียว)
- **Shelf**: w=2.5, h=4, d=0.8 (ชั้นวางเดียว)

### การจัดเรียง
- Zone A-E เรียงตาม X-axis: 10, 30, 50, 70, 90
- ระยะห่างระหว่างโซน = 20m
- จุดกึ่งกลาง Z = 25m (ครึ่งหนึ่งของ 50m)

## ตัวอย่างการใช้งาน

### แสดงเฉพาะ Zone C
```javascript
const zoneBoxes = [
    { zone: 'C', color: 0x45B7D1, x: 50, y: 2, z: 25, w: 20, h: 4, d: 50 }
];
```

### แสดง Section ใน Zone A
```javascript
const zoneBoxes = [
    { zone: 'A-S1', color: 0xFF6B6B, x: 10, y: 2, z: 1.5, w: 20, h: 4, d: 3 },
    { zone: 'A-S2', color: 0xFF6B6B, x: 10, y: 2, z: 4.5, w: 20, h: 4, d: 3 },
    { zone: 'A-S3', color: 0xFF6B6B, x: 10, y: 2, z: 7.5, w: 20, h: 4, d: 3 }
];
```

### แสดงชั้นวางเฉพาะ
```javascript
const zoneBoxes = [
    // Shelf 1 (ฝั่งขวา)
    { zone: 'Shelf-1', color: 0xFF0000, x: 1.25, y: 2, z: 0.4, w: 2.5, h: 4, d: 0.8 },
    // Shelf 2
    { zone: 'Shelf-2', color: 0x00FF00, x: 3.75, y: 2, z: 0.4, w: 2.5, h: 4, d: 0.8 }
];
```

## การ Debug

ถ้ามองไม่เห็นกล่อง:
1. เช็คว่า `y` ไม่ติดลบ (ต้อง > 0)
2. เช็คว่า `x, z` อยู่ในขอบเขต (0-100, 0-50)
3. ลอง zoom out กล้อง (scroll ออก)
4. เช็ค console ว่ามี error หรือไม่
