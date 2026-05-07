# 🛒 AIหน้าฮ่าน - Smart Mall Agentic Navigator

ระบบผู้ช่วยช้อปปิ้งอัจฉริยะที่ใช้ AI Agent ช่วยค้นหาสินค้า วางแผนเส้นทาง และให้คำแนะนำแบบเป็นส่วนตัว

## 🎯 Features

- **Semantic Search**: ค้นหาสินค้าจากอาการหรือความต้องการ (ไม่ต้องรู้ชื่อสินค้า)
- **Smart Filtering**: กรองตามราคา หมวดหมู่ และสต็อก
- **Navigation**: บอกตำแหน่งสินค้าในห้างแบบละเอียด
- **Route Planning**: วางแผนเส้นทางช้อปปิ้งและคำนวณราคารวม
- **Conversational Memory**: จำบริบทการสนทนาได้

## 🏗️ Tech Stack

- **LLM**: DeepSeek-V4-Pro (Reasoning Model)
- **Framework**: LangChain + LangGraph
- **UI**: Chainlit
- **Database**: SupaBase (PostgreSQL + pgvector)
- **Embeddings**: multilingual-e5-large
- **Deployment**: Docker + Docker Compose

## 📋 Prerequisites

- Docker & Docker Compose
- DeepSeek API Key
- SupaBase Account
- OpenAI API Key (optional, for embeddings)

## 🚀 Quick Start

### 1. Clone and Setup

```bash
cd AIE322
cp .env.example .env
```

### 2. Configure Environment

แก้ไขไฟล์ `.env`:

```env
DEEPSEEK_API_KEY=your_deepseek_api_key
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
OPENAI_API_KEY=your_openai_key  # optional
```

### 3. Setup SupaBase

1. สร้าง Project ใหม่ใน SupaBase
2. รันคำสั่ง SQL จากไฟล์ `scripts/schema.sql` ใน SQL Editor
3. Enable pgvector extension

### 4. Generate Mock Data

```bash
python scripts/generate_mockup_data.py
```

### 5. Run with Docker

```bash
docker-compose up --build
```

เปิดเบราว์เซอร์ที่ `http://localhost:8000`

## 📁 Project Structure

```
AIE322/
├── app/
│   ├── main.py              # Chainlit entry point
│   ├── agent.py             # Agent orchestration
│   ├── config.py            # Configuration
│   ├── database.py          # SupaBase client
│   ├── embeddings.py        # Embedding service
│   ├── tools.py             # Tool 1: Semantic Search
│   ├── tools2.py            # Tool 2: Stock Checker
│   ├── tools3.py            # Tool 3: Navigation
│   └── tools4.py            # Tool 4: Shopping List
├── scripts/
│   ├── generate_mockup_data.py
│   ├── load_data.py
│   └── schema.sql
├── data/
│   └── products.csv
├── .chainlit/
│   ├── config.toml
│   └── welcome.md
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

## 🧪 Testing

### Test Cases

1. **Symptom-based Search**
   ```
   "ปวดหัวมาก หายาแก้ปวดหัวหน่อย"
   ```

2. **Price Filtering**
   ```
   "หาเสื้อผ้าราคาไม่เกิน 400 บาท"
   ```

3. **Memory Test**
   ```
   User: "หาแชมพูหน่อย"
   AI: [แสดงผลลัพธ์]
   User: "แล้วมีแบรนด์อื่นไหม"
   ```

4. **Route Planning**
   ```
   "เพิ่มสินค้า P0001 ในรายการ"
   "สรุปเส้นทางช้อปปิ้งหน่อย"
   ```

## 🤖 Agent Personality

**น้องหลงทาง** มีบุคลิกดังนี้:
- ขี้เล่น กระตือรือร้น
- ใช้คำติดปาก "หลงทางรึป่าว หาของไม่เจอใช่มั้ย"
- ตอบเฉพาะสินค้า 5 หมวด
- ไม่มโนชื่อสินค้า (ใช้ข้อมูลจาก Tools เท่านั้น)

## 📊 Data Schema

สินค้า 500 รายการ แบ่งเป็น:
- อาหาร/เครื่องดื่ม (Zone A): 100 รายการ
- ของใช้ทั่วไป (Zone B): 100 รายการ
- เสื้อผ้า (Zone C): 100 รายการ
- เครื่องใช้ไฟฟ้า (Zone D): 100 รายการ
- ยาสามัญ (Zone E): 100 รายการ

## 🔧 Development

### Run Locally (without Docker)

```bash
pip install -r requirements.txt
python scripts/generate_mockup_data.py
python scripts/load_data.py
chainlit run app/main.py
```

## 📝 License

MIT License

## 👥 Contributors

- Ayo (Developer)

---

Made with ❤️ for AIE322 Course
