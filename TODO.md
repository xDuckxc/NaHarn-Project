# 🛒 Project TODO: AIหน้าฮ่าน (Smart Mall Agentic Navigator)
**Assistant Name:** น้องหลงทาง (The Smart Shopping Secretary)
**Core Engine:** DeepSeek-V4-Pro (Reasoning Model)
**Status:** Planning Phase

---

## 🏗️ 1. Technical Stack & Environment Setup
- [ ] **Infrastructure:**
    - [ ] ตั้งค่า Docker และ Docker Compose (ประกอบด้วย Services: `app-ui`, `db-loader`)
    - [ ] เตรียมไฟล์ `.env` สำหรับเก็บ API Keys (DeepSeek, SupaBase, OpenAI/Embedding)
- [ ] **Backend Framework:**
    - [ ] เลือกใช้ LangChain หรือ LangGraph สำหรับจัดการ Agentic Workflow
    - [ ] ติดตั้ง `chainlit` สำหรับระบบ Web Chat UI
- [ ] **Database & Vector Search:**
    - [ ] เชื่อมต่อ SupaBase (PostgreSQL + pgvector)
    - [ ] ติดตั้ง `sentence-transformers` หรือใช้ API สำหรับ `multilingual-e5-large`
- [ ] **Logic & Memory:**
    - [ ] คอนฟิก `ConversationBufferMemory` เพื่อรองรับ Short-term memory

---

## 📊 2. Data Preparation (Mockup 500 Items)
- [ ] **Generate CSV Data:** (ใช้ AI Agent เช่น Claude/ChatGPT Gen ข้อมูล)
    - [ ] หมวดหมู่ละ 100 รายการ: อาหาร/เครื่องดื่ม (Zone A), ของใช้ทั่วไป (Zone B), เสื้อผ้า (Zone C), เครื่องใช้ไฟฟ้า (Zone D), ยาสามัญ (Zone E)
    - [ ] **Data Fields:**
        - `id`: รหัสสินค้า
        - `name`: ชื่อสินค้า
        - `brand`: แบรนด์
        - `category`: หมวดหมู่
        - `description`: คำอธิบายภาษาไทยแบบเน้น "อาการ/ความรู้สึก"
        - `price`: ราคาสุทธิ (Float)
        - `stock_quantity`: จำนวนคงเหลือ (0-50)
        - `location_info`: JSON `{"zone": "A-E", "section": "1-5", "shelf": "1-6", "shelf_level": "1-3"}`
- [ ] **Database Ingestion:**
    - [ ] เขียนสคริปต์ Python สำหรับทำ Embedding คอลัมน์ `description`
    - [ ] อัปโหลดข้อมูลและ Vector เข้า SupaBase Table

---

## 🧠 3. Agent & Tool Development
- [ ] **Tool 1: Semantic Search & Metadata Filter**
    - [ ] พัฒนาฟังก์ชันค้นหาที่รับทั้ง Query (Vector) และ Filter (SQL สำหรับราคา/หมวดหมู่)
- [ ] **Tool 2: Stock & Availability Checker**
    - [ ] ตรวจสอบ `stock_quantity` หากเป็น 0 ให้แจ้งเตือนและแนะนำตัวใกล้เคียง
- [ ] **Tool 3: Navigation & Location Logic**
    - [ ] แปลง JSON พิกัด เป็นคำแนะนำ: Shelf 1-3 (ขวา), 4-6 (ซ้าย), Level 1 (ล่าง), 2 (กลาง), 3 (บน)
- [ ] **Tool 4: Shopping List & Route Planner (Killer Feature)**
    - [ ] ระบบ `add_to_shopping_list()` เพื่อเก็บรายการที่ User สนใจ
    - [ ] ระบบ `summarize_route()` จัดเรียงลำดับการเดินตามโซน A -> B -> C -> D -> E และสรุปราคา

---

## 💬 4. Personality & Prompt Engineering
- [ ] **System Prompt "น้องหลงทาง":**
    - [ ] กำหนดบุคลิก: ขี้เล่น, กระตือรือร้น, มีคำติดปาก "หลงทางรึป่าว หาของไม่เจอใช่มั้ย"
    - [ ] **Guardrails (กฎเหล็ก):** - ปฏิเสธคำถามนอกเหนือจากสินค้า 5 หมวด
        - **Output Verification:** ห้ามมโนชื่อสินค้า ต้องตอบตามข้อมูลจาก Tool เท่านั้น
- [ ] **Thinking Process Handling:**
    - [ ] เขียน Custom Callback Handler เพื่อดึง `reasoning_content` จาก DeepSeek
    - [ ] ส่งข้อมูลไปแสดงใน `cl.Step` ของ Chainlit เพื่อโชว์ขั้นตอนการ "คิด" ของ AI

---

## 🎨 5. UI/UX Customization (Chainlit)
- [ ] ตั้งค่าหน้า Welcome Screen ด้วยชื่อโปรเจกต์ "AIหน้าฮ่าน"
- [ ] ออกแบบการแสดงผลสินค้าในรูปแบบ Elements (Cards/Images)
- [ ] จัดทำปุ่มสำหรับสรุปเส้นทาง (Route Summary) และราคาสุทธิในตะกร้า

---

## 🧪 6. Testing & Quality Assurance (PoC Goals)
- [ ] ทดสอบการถามแบบไม่ระบุชื่อสินค้า (เช่น "ปวดท้องเมนส์กินยาอะไรดี")
- [ ] ทดสอบการกรองราคา (เช่น "หาเสื้อผ้าไม่เกิน 400 บาท")
- [ ] ทดสอบการถามต่อเนื่อง (Memory Test) เช่น "แล้วมีแบรนด์อื่นไหม"
- [ ] ทดสอบระบบ Route Planning เมื่อมีสินค้าในตะกร้าหลายหมวด
- [ ] ตรวจสอบ Log ใน Terminal ว่าแสดง Thought-Action-Observation ครบถ้วนตามโจทย์อาจารย์

---

## 📦 7. Deployment
- [ ] เขียน `docker-compose.yml` ให้รันได้ในคำสั่งเดียว
- [ ] เตรียมไฟล์ `README.md` อธิบายวิธีการรันและการใช้งานเบื้องต้น